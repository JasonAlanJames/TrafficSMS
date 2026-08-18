from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    AuthenticationError,
    AuthenticationRateLimitError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    PasswordReuseError,
    TokenExpiredError,
    UserAlreadyExistsError,
)
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    AuthenticationResponse,
    AuthenticatedUser,
    ChangeEmailRequest,
    ChangePasswordRequest,
    ChangePhoneRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    SessionInfoResponse,
    TokenResponse,
    UpdateProfileRequest,
)
from app.auth.security import (
    create_access_token,
    generate_secure_token,
    get_access_token_expires_in,
    hash_password,
    hash_token,
    verify_password,
)
from app.billing.repository import BillingRepository
from app.billing.service import BillingService
from app.billing.stripe_gateway import StripeGateway
from app.core.config import settings
from app.models.entities import User
from app.services.email import EmailService, get_email_service

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        email_service: EmailService | None = None,
    ):
        self.repository = repository
        self.email_service = email_service or get_email_service()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _token_preview(token: str | None) -> str:
        if not token:
            return "<empty>"
        if len(token) <= 16:
            return token
        return f"{token[:8]}...{token[-8:]}"

    @staticmethod
    def _is_development_logging_enabled() -> bool:
        return settings.app_env.strip().lower() == "development"

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _derive_device_name(user_agent: str | None) -> str | None:
        if not user_agent:
            return None
        normalized = user_agent.strip()
        return normalized[:255] or None

    @staticmethod
    def _normalize_identifier(identifier: str) -> str:
        normalized = identifier.strip()
        if "@" in normalized:
            return normalized.lower()
        return normalized

    def _cleanup_refresh_tokens(self, now: datetime) -> None:
        retention_cutoff = now - timedelta(days=settings.refresh_token_retention_days)
        self.repository.delete_stale_refresh_tokens(
            now=now,
            retention_cutoff=retention_cutoff,
        )

    def _log_event(
        self,
        *,
        event_type: str,
        outcome: str,
        identifier: str | None,
        user: User | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
        event_data: dict | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        self.repository.log_auth_event(
            user_id=user.id if user else None,
            identifier=identifier,
            event_type=event_type,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
            detail=detail,
            event_data=event_data,
            occurred_at=occurred_at or self._now(),
        )

    def _unlock_user_if_eligible(
        self,
        user: User,
        *,
        now: datetime,
    ) -> User:
        locked_until = self._as_utc(user.locked_until)

        if user.is_locked and locked_until is not None and locked_until <= now:
            user.is_locked = False
            user.locked_until = None
            user.failed_login_attempts = 0
            self.repository.save(user)

        return user

    def _lock_user(
        self,
        user: User,
        *,
        now: datetime,
    ) -> AccountLockedError:
        user.is_locked = True
        user.locked_until = now + timedelta(
            minutes=settings.account_lockout_minutes
        )
        self.repository.save(user)
        retry_after_seconds = settings.account_lockout_minutes * 60
        return AccountLockedError(
            "This account has been temporarily locked due to repeated sign-in failures.",
            retry_after_seconds=retry_after_seconds,
        )

    def _ensure_login_not_rate_limited(
        self,
        *,
        identifier: str,
        ip_address: str | None,
        now: datetime,
    ) -> None:
        window_start = now - timedelta(
            minutes=settings.failed_login_window_minutes
        )

        identifier_failures = self.repository.count_recent_auth_events(
            since=window_start,
            event_type="login",
            outcome="failure",
            identifier=identifier,
        )
        ip_failures = (
            self.repository.count_recent_auth_events(
                since=window_start,
                event_type="login",
                outcome="failure",
                ip_address=ip_address,
            )
            if ip_address
            else 0
        )

        if (
            identifier_failures >= settings.failed_login_rate_limit_attempts
            or ip_failures >= settings.failed_login_rate_limit_attempts
        ):
            retry_after_seconds = settings.failed_login_window_minutes * 60
            self._log_event(
                event_type="login",
                outcome="rate_limited",
                identifier=identifier,
                ip_address=ip_address,
                detail="Login rate limit reached.",
                occurred_at=now,
            )
            raise AuthenticationRateLimitError(
                retry_after_seconds=retry_after_seconds
            )

    def register(
        self,
        request: RegisterRequest,
    ) -> RegisterResponse:
        normalized_email = request.email.strip().lower()
        existing_user = self.repository.get_by_email(normalized_email)

        if existing_user is not None and existing_user.password_hash:
            raise UserAlreadyExistsError("Email address already exists.")

        if self.repository.phone_exists(
            request.phone_number,
            exclude_user_id=existing_user.id if existing_user else None,
        ):
            raise UserAlreadyExistsError("Phone number already exists.")

        now = self._now()
        user = existing_user or User(email=normalized_email)

        user.email = normalized_email
        user.phone_e164 = request.phone_number
        user.password_hash = hash_password(request.password)
        user.email_verified = False
        user.verification_token = generate_secure_token()
        if self._is_development_logging_enabled():
            logger.warning(
                "Verification token generated preview=%s length=%s",
                self._token_preview(user.verification_token),
                len(user.verification_token),
            )
        user.verification_token_expires_at = now + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        user.verification_sent_at = now
        user.phone_verified = False
        user.password_reset_token = None
        user.password_reset_expires_at = None
        user.password_reset_requested_at = None
        user.is_active = True
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.password_changed_at = now
        user.sms_consent_at = now
        user.marketing_consent_at = now if request.marketing_consent else None
        user.pending_email = None
        user.pending_email_verification_token = None
        user.pending_email_verification_expires_at = None
        user.phone_verification_requested_at = None

        if existing_user is None:
            self.repository.create(user)
        else:
            self.repository.save(user)

        if self._is_development_logging_enabled():
            logger.warning(
                "Verification token persisted preview=%s length=%s user_id=%s",
                self._token_preview(user.verification_token),
                len(user.verification_token or ""),
                user.id,
            )

        self.email_service.send_verification_email(
            recipient=user.email,
            token=user.verification_token,
        )
        self._provision_billing_customer(user)
        self._log_event(
            event_type="register",
            outcome="success",
            identifier=normalized_email,
            user=user,
            detail="Account created.",
            occurred_at=now,
        )

        return RegisterResponse(
            message="Account created. Verification email queued.",
            email_verification_sent=True,
        )

    def login(
        self,
        *,
        identifier: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticationResponse:
        now = self._now()
        normalized_identifier = self._normalize_identifier(identifier)

        self._cleanup_refresh_tokens(now)
        self._ensure_login_not_rate_limited(
            identifier=normalized_identifier,
            ip_address=ip_address,
            now=now,
        )

        user = self.repository.get_by_identifier(identifier)

        if user is not None:
            user = self._unlock_user_if_eligible(user, now=now)

        if user is None or not user.password_hash:
            self._log_event(
                event_type="login",
                outcome="failure",
                identifier=normalized_identifier,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Credentials were invalid.",
                occurred_at=now,
            )
            raise InvalidCredentialsError()

        if not user.is_active:
            self._log_event(
                event_type="login",
                outcome="failure",
                identifier=normalized_identifier,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Account is disabled.",
                occurred_at=now,
            )
            raise AccountDisabledError()

        if user.is_locked:
            locked_until = self._as_utc(user.locked_until)
            retry_after_seconds = None

            if locked_until is not None and locked_until > now:
                retry_after_seconds = int(
                    max((locked_until - now).total_seconds(), 1)
                )

            self._log_event(
                event_type="login",
                outcome="failure",
                identifier=normalized_identifier,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Account is locked.",
                occurred_at=now,
            )
            raise AccountLockedError(
                retry_after_seconds=retry_after_seconds
            )

        if not user.email_verified:
            self._log_event(
                event_type="login",
                outcome="failure",
                identifier=normalized_identifier,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Email address has not been verified.",
                occurred_at=now,
            )
            raise EmailNotVerifiedError(
                "Email address has not been verified. Request a new verification email and try again."
            )

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            user.last_failed_login = now

            if user.failed_login_attempts >= settings.failed_login_lockout_threshold:
                locked_error = self._lock_user(user, now=now)
                self._log_event(
                    event_type="login",
                    outcome="failure",
                    identifier=normalized_identifier,
                    user=user,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    detail="Account locked after repeated invalid credentials.",
                    occurred_at=now,
                )
                raise locked_error

            self.repository.save(user)
            self._log_event(
                event_type="login",
                outcome="failure",
                identifier=normalized_identifier,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Credentials were invalid.",
                occurred_at=now,
                event_data={"failed_login_attempts": user.failed_login_attempts},
            )
            raise InvalidCredentialsError()

        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.last_login = now
        self.repository.save(user)

        response = self._issue_tokens(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            now=now,
        )
        self._log_event(
            event_type="login",
            outcome="success",
            identifier=normalized_identifier,
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            detail="Sign-in succeeded.",
            occurred_at=now,
        )
        return response

    def refresh(
        self,
        *,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        now = self._now()
        self._cleanup_refresh_tokens(now)

        token_hash = hash_token(refresh_token)
        record = self.repository.get_refresh_token(token_hash)
        user = record.user if record is not None else None
        identifier = user.email.lower() if user is not None else None

        if record is None:
            self._log_event(
                event_type="refresh",
                outcome="failure",
                identifier=None,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Refresh token was not found.",
                occurred_at=now,
            )
            raise InvalidRefreshTokenError()

        if record.revoked:
            if user is not None:
                self.repository.revoke_user_refresh_tokens(
                    user.id,
                    revoked_at=now,
                )
                user.session_token_version += 1
                self.repository.save(user)

            self._log_event(
                event_type="refresh",
                outcome="replay",
                identifier=identifier,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Revoked refresh token replay detected.",
                occurred_at=now,
            )
            raise InvalidRefreshTokenError()

        expires_at = self._as_utc(record.expires_at)

        if expires_at is not None and expires_at <= now:
            self.repository.revoke_refresh_token(
                record,
                revoked_at=now,
            )
            self._log_event(
                event_type="refresh",
                outcome="failure",
                identifier=identifier,
                user=user,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Refresh token had expired.",
                occurred_at=now,
            )
            raise InvalidRefreshTokenError()

        if user is None:
            self._log_event(
                event_type="refresh",
                outcome="failure",
                identifier=None,
                ip_address=ip_address,
                user_agent=user_agent,
                detail="Refresh token had no associated user.",
                occurred_at=now,
            )
            raise InvalidRefreshTokenError()

        user = self._unlock_user_if_eligible(user, now=now)

        if not user.is_active:
            raise AccountDisabledError()

        if user.is_locked:
            locked_until = self._as_utc(user.locked_until)
            retry_after_seconds = None

            if locked_until is not None and locked_until > now:
                retry_after_seconds = int(
                    max((locked_until - now).total_seconds(), 1)
                )

            raise AccountLockedError(
                retry_after_seconds=retry_after_seconds
            )

        self.repository.touch_refresh_token(
            record,
            used_at=now,
        )

        token_pair = self._build_token_pair(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            now=now,
        )

        self.repository.revoke_refresh_token(
            record,
            revoked_at=now,
            replaced_by_token_id=token_pair["record_id"],
        )

        self._log_event(
            event_type="refresh",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            detail="Refresh token rotated successfully.",
            occurred_at=now,
        )

        return token_pair["tokens"]

    def logout(
        self,
        *,
        refresh_token: str,
    ) -> MessageResponse:
        now = self._now()
        record = self.repository.get_refresh_token(hash_token(refresh_token))

        if record and not record.revoked:
            self.repository.revoke_refresh_token(
                record,
                revoked_at=now,
            )
            self._log_event(
                event_type="logout",
                outcome="success",
                identifier=record.user.email.lower() if record.user else None,
                user=record.user,
                detail="Refresh token revoked.",
                occurred_at=now,
            )

        return MessageResponse(message="Successfully logged out.")

    def logout_all(
        self,
        *,
        user: User,
    ) -> MessageResponse:
        now = self._now()
        user.session_token_version += 1
        self.repository.save(user)
        self.repository.revoke_user_refresh_tokens(
            user.id,
            revoked_at=now,
        )
        self._log_event(
            event_type="logout_all",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="All active sessions were revoked.",
            occurred_at=now,
        )
        return MessageResponse(message="Successfully logged out from all devices.")

    def list_sessions(
        self,
        *,
        user: User,
        current_session_id: UUID | None,
    ) -> list[SessionInfoResponse]:
        now = self._now()
        self._cleanup_refresh_tokens(now)

        sessions = self.repository.get_active_refresh_tokens_for_user(
            user_id=user.id,
            now=now,
        )
        return [
            SessionInfoResponse(
                id=session.id,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                device_name=session.device_name,
                created_at=self._as_utc(session.created_at) or session.created_at,
                last_used_at=self._as_utc(session.last_used_at),
                expires_at=self._as_utc(session.expires_at) or session.expires_at,
                is_current=current_session_id == session.id,
            )
            for session in sessions
        ]

    def revoke_session(
        self,
        *,
        user: User,
        session_id: UUID,
    ) -> MessageResponse:
        now = self._now()
        session = self.repository.get_refresh_token_for_user(
            user_id=user.id,
            token_id=session_id,
        )

        if session is None:
            raise AuthenticationError("Session was not found.")

        if not session.revoked:
            self.repository.revoke_refresh_token(
                session,
                revoked_at=now,
            )

        self._log_event(
            event_type="session_revoke",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="A single session was revoked.",
            event_data={"session_id": str(session_id)},
            occurred_at=now,
        )
        return MessageResponse(message="Session revoked.")

    def get_user(
        self,
        user_id: int,
    ) -> User | None:
        return self.repository.get_by_id(user_id)

    def verify_email(
        self,
        *,
        token: str,
    ) -> MessageResponse:
        now = self._now()
        if self._is_development_logging_enabled():
            logger.warning(
                "Verification token received preview=%s length=%s",
                self._token_preview(token),
                len(token),
            )
        user = self.repository.get_by_verification_token(token)

        if self._is_development_logging_enabled():
            logger.warning(
                "Verification token lookup result found=%s method=database_lookup_raw_token",
                user is not None,
            )

        if user is None:
            self._log_event(
                event_type="verify_email",
                outcome="failure",
                identifier=None,
                detail="Verification token was invalid.",
                occurred_at=now,
            )
            raise InvalidTokenError("Email verification token is invalid.")

        expires_at = self._as_utc(user.verification_token_expires_at)

        if expires_at is not None and expires_at <= now:
            if self._is_development_logging_enabled():
                logger.warning(
                    "Verification token validation failed reason=expired preview=%s expires_at=%s now=%s",
                    self._token_preview(token),
                    expires_at.isoformat(),
                    now.isoformat(),
                )
            self._log_event(
                event_type="verify_email",
                outcome="failure",
                identifier=user.email.lower(),
                user=user,
                detail="Verification token had expired.",
                occurred_at=now,
            )
            raise TokenExpiredError(
                "Email verification token has expired. Request a new verification email."
            )

        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        user.verification_sent_at = None
        self.repository.save(user)
        self._log_event(
            event_type="verify_email",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="Email address verified.",
            occurred_at=now,
        )

        return MessageResponse(message="Email address verified.")

    def resend_verification(
        self,
        *,
        email: str,
    ) -> MessageResponse:
        now = self._now()
        normalized_email = email.strip().lower()
        user = self.repository.get_by_email(normalized_email)

        if user is None or user.email_verified or not user.password_hash:
            return MessageResponse(
                message="If the account exists and still needs verification, a new verification email will be sent."
            )

        sent_at = self._as_utc(user.verification_sent_at)
        if (
            sent_at is not None
            and sent_at
            >= now - timedelta(seconds=settings.email_verification_resend_cooldown_seconds)
        ):
            return MessageResponse(
                message="If the account exists and still needs verification, a new verification email will be sent."
            )

        expires_at = self._as_utc(user.verification_token_expires_at)
        if expires_at is None or expires_at <= now or not user.verification_token:
            user.verification_token = generate_secure_token()
            user.verification_token_expires_at = now + timedelta(
                hours=settings.email_verification_token_expire_hours
            )

        user.verification_sent_at = now
        self.repository.save(user)
        self.email_service.send_resend_verification_email(
            recipient=user.email,
            token=user.verification_token,
        )
        self._log_event(
            event_type="verify_email_resend",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="Verification email reissued.",
            occurred_at=now,
        )
        return MessageResponse(
            message="If the account exists and still needs verification, a new verification email will be sent."
        )

    def forgot_password(
        self,
        *,
        email: str,
    ) -> MessageResponse:
        now = self._now()
        normalized_email = email.strip().lower()
        user = self.repository.get_by_email(normalized_email)

        if user and user.password_hash:
            requested_at = self._as_utc(user.password_reset_requested_at)
            within_cooldown = (
                requested_at is not None
                and requested_at
                >= now - timedelta(seconds=settings.password_reset_resend_cooldown_seconds)
            )

            if not within_cooldown:
                user.password_reset_token = generate_secure_token()
                user.password_reset_expires_at = now + timedelta(
                    hours=settings.password_reset_token_expire_hours
                )
                user.password_reset_requested_at = now
                self.repository.save(user)
                self.email_service.send_password_reset_email(
                    recipient=user.email,
                    token=user.password_reset_token,
                )
                self._log_event(
                    event_type="password_reset_request",
                    outcome="success",
                    identifier=user.email.lower(),
                    user=user,
                    detail="Password reset token issued.",
                    occurred_at=now,
                )

        return MessageResponse(
            message="If the account exists, a password reset email will be sent."
        )

    def reset_password(
        self,
        *,
        token: str,
        new_password: str,
    ) -> MessageResponse:
        now = self._now()
        user = self.repository.get_by_password_reset_token(token)

        if user is None:
            self._log_event(
                event_type="password_reset",
                outcome="failure",
                identifier=None,
                detail="Password reset token was invalid.",
                occurred_at=now,
            )
            raise InvalidTokenError("Password reset token is invalid.")

        expires_at = self._as_utc(user.password_reset_expires_at)
        if expires_at is not None and expires_at <= now:
            self._log_event(
                event_type="password_reset",
                outcome="failure",
                identifier=user.email.lower(),
                user=user,
                detail="Password reset token had expired.",
                occurred_at=now,
            )
            raise TokenExpiredError("Password reset token has expired.")

        if user.password_hash and verify_password(new_password, user.password_hash):
            raise PasswordReuseError()

        user.password_hash = hash_password(new_password)
        user.password_changed_at = now
        user.password_reset_token = None
        user.password_reset_expires_at = None
        user.password_reset_requested_at = None
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.session_token_version += 1
        self.repository.save(user)
        self.repository.revoke_user_refresh_tokens(
            user.id,
            revoked_at=now,
        )
        self._log_event(
            event_type="password_reset",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="Password reset completed successfully.",
            occurred_at=now,
        )

        return MessageResponse(message="Password updated successfully.")

    def update_profile(
        self,
        *,
        user: User,
        request: UpdateProfileRequest,
    ) -> User:
        user.home_location = request.home_location
        user.work_location = request.work_location
        user.gym_location = request.gym_location
        user.school_location = request.school_location

        if request.default_state is not None:
            user.default_state = request.default_state

        if request.default_country is not None:
            user.default_country = request.default_country

        updated = self.repository.save(user)
        self._log_event(
            event_type="profile_update",
            outcome="success",
            identifier=updated.email.lower(),
            user=updated,
            detail="Profile updated.",
        )
        return updated

    def change_password(
        self,
        *,
        user: User,
        request: ChangePasswordRequest,
    ) -> MessageResponse:
        now = self._now()

        if not user.password_hash or not verify_password(
            request.current_password,
            user.password_hash,
        ):
            raise InvalidCredentialsError("Current password is incorrect.")

        if verify_password(request.new_password, user.password_hash):
            raise PasswordReuseError()

        user.password_hash = hash_password(request.new_password)
        user.password_changed_at = now
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.session_token_version += 1
        self.repository.save(user)
        self.repository.revoke_user_refresh_tokens(
            user.id,
            revoked_at=now,
        )
        self._log_event(
            event_type="password_change",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="Password changed and all sessions revoked.",
            occurred_at=now,
        )

        return MessageResponse(
            message="Password updated. Please sign in again on this device."
        )

    def request_email_change(
        self,
        *,
        user: User,
        request: ChangeEmailRequest,
    ) -> MessageResponse:
        now = self._now()
        normalized_email = request.new_email.strip().lower()

        if not user.password_hash or not verify_password(
            request.current_password,
            user.password_hash,
        ):
            raise InvalidCredentialsError("Current password is incorrect.")

        if normalized_email == user.email.lower():
            raise AuthenticationError(
                "New email address must be different from the current email."
            )

        existing_user = self.repository.get_by_email(normalized_email)
        if existing_user is not None and existing_user.id != user.id:
            raise UserAlreadyExistsError("Email address already exists.")

        user.pending_email = normalized_email
        user.pending_email_verification_token = generate_secure_token()
        user.pending_email_verification_expires_at = now + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        self.repository.save(user)
        self._log_event(
            event_type="email_change_request",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="Email change verification issued.",
            event_data={"pending_email": normalized_email},
            occurred_at=now,
        )
        return MessageResponse(
            message="Email change requested. Verify the new address using the issued token."
        )

    def confirm_email_change(
        self,
        *,
        token: str,
    ) -> MessageResponse:
        now = self._now()
        user = self.repository.get_by_pending_email_verification_token(token)

        if user is None or not user.pending_email:
            raise InvalidTokenError("Email change token is invalid.")

        expires_at = self._as_utc(user.pending_email_verification_expires_at)
        if expires_at is not None and expires_at <= now:
            raise TokenExpiredError("Email change token has expired.")

        existing_user = self.repository.get_by_email(user.pending_email)
        if existing_user is not None and existing_user.id != user.id:
            raise UserAlreadyExistsError("Email address already exists.")

        old_email = user.email
        user.email = user.pending_email
        user.email_verified = True
        user.pending_email = None
        user.pending_email_verification_token = None
        user.pending_email_verification_expires_at = None
        self.repository.save(user)
        self._log_event(
            event_type="email_change_confirm",
            outcome="success",
            identifier=user.email.lower(),
            user=user,
            detail="Email address updated after verification.",
            event_data={"old_email": old_email},
            occurred_at=now,
        )
        return MessageResponse(message="Email address updated successfully.")

    def change_phone(
        self,
        *,
        user: User,
        request: ChangePhoneRequest,
    ) -> AuthenticatedUser:
        now = self._now()

        if not user.password_hash or not verify_password(
            request.current_password,
            user.password_hash,
        ):
            raise InvalidCredentialsError("Current password is incorrect.")

        if self.repository.phone_exists(
            request.phone_number,
            exclude_user_id=user.id,
        ):
            raise UserAlreadyExistsError("Phone number already exists.")

        user.phone_e164 = request.phone_number
        user.phone_verified = False
        user.phone_verification_requested_at = now
        updated = self.repository.save(user)
        self._log_event(
            event_type="phone_change",
            outcome="success",
            identifier=updated.email.lower(),
            user=updated,
            detail="Phone number updated and marked unverified.",
            occurred_at=now,
        )
        return AuthenticatedUser.model_validate(updated)

    def _issue_tokens(
        self,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
        now: datetime | None = None,
    ) -> AuthenticationResponse:
        token_pair = self._build_token_pair(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
            now=now or self._now(),
        )

        return AuthenticationResponse(
            user=AuthenticatedUser.model_validate(user),
            **token_pair["tokens"].model_dump(),
        )

    def _build_token_pair(
        self,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
        now: datetime,
    ) -> dict[str, object]:
        refresh_token = generate_secure_token()
        record = self.repository.store_refresh_token(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=now + timedelta(
                days=settings.refresh_token_expire_days
            ),
            ip_address=ip_address,
            user_agent=user_agent,
            device_name=self._derive_device_name(user_agent),
        )

        access_token = create_access_token(
            subject=str(user.id),
            additional_claims={
                "email": user.email,
                "subscription_tier": user.subscription_plan or "free",
                "subscription_status": user.subscription_status,
                "session_id": str(record.id),
                "token_version": user.session_token_version,
            },
        )

        return {
            "record_id": record.id,
            "tokens": TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=get_access_token_expires_in(),
            ),
        }

    def _provision_billing_customer(self, user: User) -> None:
        if not settings.stripe_secret_key:
            return

        service = BillingService(
            BillingRepository(self.repository.db),
            stripe_gateway=StripeGateway(settings.stripe_secret_key),
        )
        service.provision_customer_for_new_user(user)

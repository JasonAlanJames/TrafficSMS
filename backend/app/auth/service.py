from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.auth.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    InvalidTokenError,
    TokenExpiredError,
    UserAlreadyExistsError,
)
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    AuthenticationResponse,
    AuthenticatedUser,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.auth.security import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.config import settings
from app.models.entities import User


class AuthService:
    def __init__(self, repository: AuthRepository):
        self.repository = repository

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

        now = datetime.now(UTC)
        user = existing_user or User(email=normalized_email)

        user.email = normalized_email
        user.phone_e164 = request.phone_number
        user.password_hash = hash_password(request.password)
        user.email_verified = False
        user.verification_token = generate_secure_token()
        user.verification_token_expires_at = now + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        user.phone_verified = False
        user.password_reset_token = None
        user.password_reset_expires_at = None
        user.is_active = True
        user.is_locked = False
        user.failed_login_attempts = 0
        user.last_failed_login = None
        user.password_changed_at = now
        user.sms_consent_at = now
        user.marketing_consent_at = now if request.marketing_consent else None

        if existing_user is None:
            self.repository.create(user)
        else:
            self.repository.save(user)

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
        user = self.repository.get_by_identifier(identifier)
        now = datetime.now(UTC)

        if user is None or not user.password_hash:
            raise InvalidCredentialsError()

        if not user.is_active:
            raise AccountDisabledError()

        if user.is_locked:
            raise AccountLockedError()

        if not user.email_verified:
            raise EmailNotVerifiedError()

        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            user.last_failed_login = now

            if user.failed_login_attempts >= settings.failed_login_lockout_threshold:
                user.is_locked = True
                self.repository.save(user)
                raise AccountLockedError()

            self.repository.save(user)
            raise InvalidCredentialsError()

        user.failed_login_attempts = 0
        user.last_login = now
        self.repository.save(user)

        return self._issue_tokens(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def refresh(
        self,
        *,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        now = datetime.now(UTC)
        token_hash = hash_token(refresh_token)
        record = self.repository.get_refresh_token(token_hash)

        if record is None or record.revoked:
            raise InvalidRefreshTokenError()

        if record.expires_at <= now:
            self.repository.revoke_refresh_token(
                record,
                revoked_at=now,
            )
            raise InvalidRefreshTokenError()

        user = record.user

        if user is None:
            raise InvalidRefreshTokenError()

        if not user.is_active:
            raise AccountDisabledError()

        if user.is_locked:
            raise AccountLockedError()

        token_pair = self._build_token_pair(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.repository.revoke_refresh_token(
            record,
            revoked_at=now,
            replaced_by_token_id=token_pair["record_id"],
        )

        return token_pair["tokens"]

    def logout(
        self,
        *,
        refresh_token: str,
    ) -> MessageResponse:
        token_hash = hash_token(refresh_token)
        record = self.repository.get_refresh_token(token_hash)

        if record and not record.revoked:
            self.repository.revoke_refresh_token(
                record,
                revoked_at=datetime.now(UTC),
            )

        return MessageResponse(message="Successfully logged out.")

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
        user = self.repository.get_by_verification_token(token)
        now = datetime.now(UTC)

        if user is None:
            raise InvalidTokenError("Email verification token is invalid.")

        if (
            user.verification_token_expires_at is not None
            and user.verification_token_expires_at <= now
        ):
            raise TokenExpiredError("Email verification token has expired.")

        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires_at = None
        self.repository.save(user)

        return MessageResponse(message="Email address verified.")

    def forgot_password(
        self,
        *,
        email: str,
    ) -> MessageResponse:
        user = self.repository.get_by_email(email)

        if user and user.password_hash:
            user.password_reset_token = generate_secure_token()
            user.password_reset_expires_at = datetime.now(UTC) + timedelta(
                hours=settings.password_reset_token_expire_hours
            )
            self.repository.save(user)

        return MessageResponse(
            message="If the account exists, a password reset email will be sent."
        )

    def reset_password(
        self,
        *,
        token: str,
        new_password: str,
    ) -> MessageResponse:
        user = self.repository.get_by_password_reset_token(token)
        now = datetime.now(UTC)

        if user is None:
            raise InvalidTokenError("Password reset token is invalid.")

        if (
            user.password_reset_expires_at is not None
            and user.password_reset_expires_at <= now
        ):
            raise TokenExpiredError("Password reset token has expired.")

        user.password_hash = hash_password(new_password)
        user.password_changed_at = now
        user.password_reset_token = None
        user.password_reset_expires_at = None
        user.failed_login_attempts = 0
        user.is_locked = False
        self.repository.save(user)
        self.repository.revoke_user_refresh_tokens(
            user.id,
            revoked_at=now,
        )

        return MessageResponse(message="Password updated successfully.")

    def _issue_tokens(
        self,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthenticationResponse:
        token_pair = self._build_token_pair(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return AuthenticationResponse(
            user=AuthenticatedUser.model_validate(user),
            tokens=token_pair["tokens"],
        )

    def _build_token_pair(
        self,
        *,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, object]:
        access_token = create_access_token(subject=str(user.id))
        refresh_token = generate_secure_token()
        record = self.repository.store_refresh_token(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(
                days=settings.refresh_token_expire_days
            ),
            ip_address=ip_address,
            user_agent=user_agent,
        )

        return {
            "record_id": record.id,
            "tokens": TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
            ),
        }

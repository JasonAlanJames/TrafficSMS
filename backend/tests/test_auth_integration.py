from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token, verify_password
from app.core.config import settings
from app.models.entities import User
from app.models.refresh_token import RefreshToken


def register_payload(email: str = "driver@test.trafficsms.com") -> dict[str, object]:
    return {
        "email": email,
        "password": "SecurePass1!",
        "phone_number": "+17145551234",
        "sms_consent": True,
        "marketing_consent": True,
    }


def create_verified_user(client, db_session: Session, email: str = "driver@test.trafficsms.com") -> User:
    response = client.post("/auth/register", json=register_payload(email=email))
    assert response.status_code == 201

    user = db_session.scalar(
        select(User).where(User.email == email)
    )
    assert user is not None

    verify_response = client.get(
        "/auth/verify-email",
        params={"token": user.verification_token},
    )
    assert verify_response.status_code == 200

    db_session.refresh(user)
    return user


def login(client, email: str = "driver@test.trafficsms.com", password: str = "SecurePass1!"):
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
            "remember_me": True,
        },
    )
    assert response.status_code == 200
    return response


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@contextmanager
def temporary_auth_settings(**overrides):
    original_values = {
        key: getattr(settings, key)
        for key in overrides
    }

    try:
        for key, value in overrides.items():
            setattr(settings, key, value)
        yield
    finally:
        for key, value in original_values.items():
            setattr(settings, key, value)


class FakeSMTP:
    sent_messages: list[EmailMessage] = []
    login_calls: list[tuple[str, str]] = []
    starttls_calls = 0
    connections: list[tuple[str, int]] = []

    def __init__(self, host: str, port: int, timeout: int | None = None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.closed = False
        type(self).connections.append((host, port))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.quit()
        return False

    def ehlo(self):
        return (250, b"ok")

    def starttls(self, context=None):
        type(self).starttls_calls += 1
        return (220, b"ready")

    def login(self, username: str, password: str):
        type(self).login_calls.append((username, password))
        return (235, b"authenticated")

    def send_message(self, message: EmailMessage):
        type(self).sent_messages.append(message)
        return {}

    def quit(self):
        self.closed = True
        return (221, b"bye")

    @classmethod
    def reset(cls):
        cls.sent_messages = []
        cls.login_calls = []
        cls.starttls_calls = 0
        cls.connections = []


class FailingSMTP(FakeSMTP):
    def send_message(self, message: EmailMessage):
        raise RuntimeError("SMTP send failed")


@pytest.fixture()
def smtp_outbox(monkeypatch):
    from app.services import email as email_service_module

    FakeSMTP.reset()
    email_service_module.get_email_service.cache_clear()
    monkeypatch.setattr(email_service_module.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service_module.smtplib, "SMTP_SSL", FakeSMTP)

    with temporary_auth_settings(
        smtp_host="smtp.test.local",
        smtp_port=2525,
        smtp_username="mailer",
        smtp_password="secret",
        email_enabled=True,
        mail_from="no-reply@trafficsms.test",
        mail_from_name="TrafficSMS Test",
        email_reply_to="support@trafficsms.test",
        smtp_tls=True,
        smtp_ssl=False,
        smtp_timeout_seconds=5,
        frontend_url="https://trafficsms.test",
    ):
        yield FakeSMTP

    email_service_module.get_email_service.cache_clear()


@pytest.fixture()
def failing_smtp(monkeypatch):
    from app.services import email as email_service_module

    FailingSMTP.reset()
    email_service_module.get_email_service.cache_clear()
    monkeypatch.setattr(email_service_module.smtplib, "SMTP", FailingSMTP)
    monkeypatch.setattr(email_service_module.smtplib, "SMTP_SSL", FailingSMTP)

    with temporary_auth_settings(
        smtp_host="smtp.test.local",
        smtp_port=2525,
        smtp_username="",
        smtp_password="",
        email_enabled=True,
        mail_from="no-reply@trafficsms.test",
        mail_from_name="TrafficSMS Test",
        email_reply_to="support@trafficsms.test",
        smtp_tls=False,
        smtp_ssl=False,
        smtp_timeout_seconds=5,
        frontend_url="https://trafficsms.test",
    ):
        yield FailingSMTP

    email_service_module.get_email_service.cache_clear()


def message_text_body(message: EmailMessage) -> str:
    body = message.get_body(preferencelist=("plain",))
    assert body is not None
    return body.get_content()


def message_html_body(message: EmailMessage) -> str:
    body = message.get_body(preferencelist=("html",))
    assert body is not None
    return body.get_content()


def test_registration_verification_login_and_current_user(client, db_session: Session):
    response = client.post("/auth/register", json=register_payload())
    assert response.status_code == 201

    user = db_session.scalar(
        select(User).where(User.email == "driver@test.trafficsms.com")
    )
    assert user is not None
    assert user.email_verified is False
    assert user.sms_consent_at is not None
    assert user.marketing_consent_at is not None
    assert user.password_hash != "SecurePass1!"
    assert verify_password("SecurePass1!", user.password_hash)

    verify_response = client.get(
        "/auth/verify-email",
        params={"token": user.verification_token},
    )
    assert verify_response.status_code == 200

    db_session.refresh(user)
    assert user.email_verified is True
    assert user.verification_token is None

    login_response = login(client)
    body = login_response.json()

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["expires_in"] == 1800
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "driver@test.trafficsms.com"

    claims = decode_access_token(body["access_token"])
    assert claims["sub"] == str(user.id)
    assert claims["email"] == "driver@test.trafficsms.com"
    assert claims["subscription_tier"] == "free"
    assert claims["type"] == "access"

    me_response = client.get("/users/me", headers=auth_headers(body["access_token"]))
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "driver@test.trafficsms.com"


def test_refresh_rotation_and_logout(client, db_session: Session):
    create_verified_user(client, db_session)
    login_response = login(client)
    original_refresh = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh},
    )
    assert refresh_response.status_code == 200

    refreshed_body = refresh_response.json()
    assert refreshed_body["refresh_token"] != original_refresh

    refresh_records = db_session.scalars(
        select(RefreshToken).order_by(RefreshToken.created_at.asc())
    ).all()
    assert len(refresh_records) == 2
    assert refresh_records[0].revoked is True
    assert refresh_records[0].replaced_by_token_id == refresh_records[1].id

    logout_response = client.post(
        "/auth/logout",
        json={"refresh_token": refreshed_body["refresh_token"]},
    )
    assert logout_response.status_code == 200

    invalid_refresh = client.post(
        "/auth/refresh",
        json={"refresh_token": refreshed_body["refresh_token"]},
    )
    assert invalid_refresh.status_code == 401


def test_logout_all_revokes_all_active_sessions(client, db_session: Session):
    create_verified_user(client, db_session)
    first_login = login(client).json()
    second_login = login(client).json()

    logout_all_response = client.post(
        "/auth/logout-all",
        headers=auth_headers(first_login["access_token"]),
    )
    assert logout_all_response.status_code == 200

    refresh_records = db_session.scalars(select(RefreshToken)).all()
    assert refresh_records
    assert all(record.revoked for record in refresh_records)

    refresh_after_logout_all = client.post(
        "/auth/refresh",
        json={"refresh_token": second_login["refresh_token"]},
    )
    assert refresh_after_logout_all.status_code == 401


def test_forgot_password_and_reset_password_revokes_existing_tokens(client, db_session: Session):
    user = create_verified_user(client, db_session)
    login_response = login(client).json()

    forgot_response = client.post(
        "/auth/forgot-password",
        json={"email": user.email},
    )
    assert forgot_response.status_code == 200

    db_session.refresh(user)
    assert user.password_reset_token is not None

    reset_response = client.post(
        "/auth/reset-password",
        json={
            "token": user.password_reset_token,
            "new_password": "EvenBetter2!",
        },
    )
    assert reset_response.status_code == 200

    db_session.refresh(user)
    assert user.password_reset_token is None
    assert user.password_changed_at is not None
    assert user.is_locked is False

    refresh_records = db_session.scalars(select(RefreshToken)).all()
    assert refresh_records
    assert all(record.revoked for record in refresh_records)

    old_password_login = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": "SecurePass1!",
            "remember_me": True,
        },
    )
    assert old_password_login.status_code == 401

    new_password_login = client.post(
        "/auth/login",
        json={
            "email": user.email,
            "password": "EvenBetter2!",
            "remember_me": True,
        },
    )
    assert new_password_login.status_code == 200


def test_verify_email_rejects_expired_tokens(client, db_session: Session):
    response = client.post("/auth/register", json=register_payload(email="expired@test.trafficsms.com"))
    assert response.status_code == 201

    user = db_session.scalar(
        select(User).where(User.email == "expired@test.trafficsms.com")
    )
    assert user is not None

    user.verification_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(user)
    db_session.commit()

    verify_response = client.get(
        "/auth/verify-email",
        params={"token": user.verification_token},
    )
    assert verify_response.status_code == 400
    assert "expired" in verify_response.json()["detail"].lower()


def test_registration_rejects_duplicate_email_and_phone(client, db_session: Session):
    first = client.post("/auth/register", json=register_payload())
    assert first.status_code == 201

    duplicate_email = client.post("/auth/register", json=register_payload())
    assert duplicate_email.status_code == 409
    assert "exists" in duplicate_email.json()["detail"].lower()

    duplicate_phone = client.post(
        "/auth/register",
        json=register_payload(email="another@test.trafficsms.com"),
    )
    assert duplicate_phone.status_code == 409
    assert "phone" in duplicate_phone.json()["detail"].lower()


def test_registration_triggers_smtp_send(client, db_session: Session, smtp_outbox):
    response = client.post("/auth/register", json=register_payload(email="mail@test.trafficsms.com"))
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == "mail@test.trafficsms.com"))
    assert user is not None

    assert len(smtp_outbox.sent_messages) == 1
    assert smtp_outbox.connections == [("smtp.test.local", 2525)]
    assert smtp_outbox.starttls_calls == 1
    assert smtp_outbox.login_calls == [("mailer", "secret")]

    message = smtp_outbox.sent_messages[0]
    assert message["To"] == "mail@test.trafficsms.com"
    assert message["Subject"] == "Verify your TrafficSMS account"
    assert user.verification_token in message_text_body(message)
    assert "https://trafficsms.test/verify-email?token=" in message_text_body(message)
    assert "/api/auth/verify-email" not in message_text_body(message)
    assert "Verify account" in message_html_body(message)
    assert message["From"] == "TrafficSMS Test <no-reply@trafficsms.test>"
    assert message["Reply-To"] == "support@trafficsms.test"
    assert "Verify your TrafficSMS account" in message_html_body(message)


def test_password_reset_triggers_smtp_send(client, db_session: Session, smtp_outbox):
    user = create_verified_user(client, db_session, email="resetmail@test.trafficsms.com")

    response = client.post("/auth/forgot-password", json={"email": user.email})
    assert response.status_code == 200

    db_session.refresh(user)
    assert user.password_reset_token is not None
    assert len(smtp_outbox.sent_messages) == 2

    message = smtp_outbox.sent_messages[-1]
    assert message["To"] == user.email
    assert message["Subject"] == "Reset your TrafficSMS password"
    assert user.password_reset_token in message_text_body(message)
    assert "https://trafficsms.test/reset-password?token=" in message_text_body(message)
    assert "/api/auth/reset-password" not in message_text_body(message)
    assert "Reset password" in message_html_body(message)
    for forbidden_copy in (
        "API client",
        "Reset token",
        "Reset endpoint",
        "Use the token below",
        "existing password reset flow",
    ):
        assert forbidden_copy not in message_text_body(message)
        assert forbidden_copy not in message_html_body(message)
    assert "Reset your TrafficSMS password" in message_html_body(message)


def test_resend_verification_triggers_smtp_send(client, db_session: Session, smtp_outbox):
    response = client.post("/auth/register", json=register_payload(email="resendmail@test.trafficsms.com"))
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == "resendmail@test.trafficsms.com"))
    assert user is not None
    original_message_count = len(smtp_outbox.sent_messages)

    user.verification_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    user.verification_sent_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.add(user)
    db_session.commit()

    resend_response = client.post("/auth/resend-verification", json={"email": user.email})
    assert resend_response.status_code == 200

    db_session.refresh(user)
    assert len(smtp_outbox.sent_messages) == original_message_count + 1
    message = smtp_outbox.sent_messages[-1]
    assert message["To"] == user.email
    assert message["Subject"] == "Verify your TrafficSMS account"
    assert user.verification_token in message_text_body(message)
    assert "A new verification link was requested for your account." in message_text_body(message)


def test_registration_succeeds_when_smtp_fails(client, db_session: Session, failing_smtp):
    response = client.post("/auth/register", json=register_payload(email="smtpfail@test.trafficsms.com"))
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == "smtpfail@test.trafficsms.com"))
    assert user is not None
    assert user.verification_token is not None
    assert len(failing_smtp.sent_messages) == 0


def test_resend_verification_reissues_expired_token(client, db_session: Session):
    response = client.post("/auth/register", json=register_payload(email="resend@test.trafficsms.com"))
    assert response.status_code == 201

    user = db_session.scalar(
        select(User).where(User.email == "resend@test.trafficsms.com")
    )
    assert user is not None
    original_token = user.verification_token

    user.verification_token_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    user.verification_sent_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.add(user)
    db_session.commit()

    resend_response = client.post(
        "/auth/resend-verification",
        json={"email": user.email},
    )
    assert resend_response.status_code == 200

    db_session.refresh(user)
    assert user.verification_token is not None
    assert user.verification_token != original_token
    assert user.verification_sent_at is not None
    assert user.verification_token_expires_at is not None
    assert as_utc(user.verification_token_expires_at) > datetime.now(UTC)


def test_password_reset_cooldown_and_expired_reset_token(client, db_session: Session):
    user = create_verified_user(client, db_session, email="reset@test.trafficsms.com")

    first_reset = client.post(
        "/auth/forgot-password",
        json={"email": user.email},
    )
    assert first_reset.status_code == 200

    db_session.refresh(user)
    original_token = user.password_reset_token
    original_requested_at = user.password_reset_requested_at
    assert original_token is not None
    assert original_requested_at is not None

    second_reset = client.post(
        "/auth/forgot-password",
        json={"email": user.email},
    )
    assert second_reset.status_code == 200

    db_session.refresh(user)
    assert user.password_reset_token == original_token
    assert user.password_reset_requested_at == original_requested_at

    user.password_reset_expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(user)
    db_session.commit()

    expired_reset = client.post(
        "/auth/reset-password",
        json={
            "token": original_token,
            "new_password": "AnotherStrong3!",
        },
    )
    assert expired_reset.status_code == 400
    assert "expired" in expired_reset.json()["detail"].lower()


def test_refresh_replay_invalidates_existing_access_tokens(client, db_session: Session):
    user = create_verified_user(client, db_session, email="replay@test.trafficsms.com")
    login_body = login(client, email=user.email).json()

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": login_body["refresh_token"]},
    )
    assert refreshed.status_code == 200

    replay = client.post(
        "/auth/refresh",
        json={"refresh_token": login_body["refresh_token"]},
    )
    assert replay.status_code == 401

    db_session.refresh(user)
    assert user.session_token_version == 1

    invalidated_access = client.get(
        "/users/me",
        headers=auth_headers(login_body["access_token"]),
    )
    assert invalidated_access.status_code == 401
    assert "session" in invalidated_access.json()["detail"].lower()


def test_login_rate_limit_returns_retry_after(client, db_session: Session):
    user = create_verified_user(client, db_session, email="ratelimit@test.trafficsms.com")

    with temporary_auth_settings(
        failed_login_lockout_threshold=99,
        failed_login_rate_limit_attempts=2,
        failed_login_window_minutes=1,
    ):
        first = client.post(
            "/auth/login",
            json={"email": user.email, "password": "WrongPass1!", "remember_me": True},
        )
        second = client.post(
            "/auth/login",
            json={"email": user.email, "password": "WrongPass1!", "remember_me": True},
        )
        third = client.post(
            "/auth/login",
            json={"email": user.email, "password": "WrongPass1!", "remember_me": True},
        )

    assert first.status_code == 401
    assert second.status_code == 401
    assert third.status_code == 429
    assert third.headers["Retry-After"] == "60"


def test_account_lockout_auto_unlocks_after_expiration(client, db_session: Session):
    user = create_verified_user(client, db_session, email="lockout@test.trafficsms.com")

    with temporary_auth_settings(
        failed_login_lockout_threshold=2,
        account_lockout_minutes=1,
        failed_login_rate_limit_attempts=99,
    ):
        first = client.post(
            "/auth/login",
            json={"email": user.email, "password": "WrongPass1!", "remember_me": True},
        )
        second = client.post(
            "/auth/login",
            json={"email": user.email, "password": "WrongPass1!", "remember_me": True},
        )

        assert first.status_code == 401
        assert second.status_code == 423
        assert second.headers["Retry-After"] == "60"

        db_session.refresh(user)
        user.locked_until = datetime.now(UTC) - timedelta(seconds=1)
        db_session.add(user)
        db_session.commit()

        unlocked_login = client.post(
            "/auth/login",
            json={"email": user.email, "password": "SecurePass1!", "remember_me": True},
        )

    assert unlocked_login.status_code == 200
    db_session.refresh(user)
    assert user.is_locked is False
    assert user.failed_login_attempts == 0


def test_session_listing_and_single_session_revocation(client, db_session: Session):
    create_verified_user(client, db_session, email="sessions@test.trafficsms.com")
    first_login = login(client, email="sessions@test.trafficsms.com").json()
    second_login = login(client, email="sessions@test.trafficsms.com").json()

    sessions_response = client.get(
        "/auth/sessions",
        headers=auth_headers(first_login["access_token"]),
    )
    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert len(sessions) == 2

    current_session = next(session for session in sessions if session["is_current"] is True)
    other_session = next(session for session in sessions if session["id"] != current_session["id"])

    revoke_response = client.delete(
        f"/auth/sessions/{other_session['id']}",
        headers=auth_headers(first_login["access_token"]),
    )
    assert revoke_response.status_code == 200

    revoked_session_access = client.get(
        "/users/me",
        headers=auth_headers(second_login["access_token"]),
    )
    assert revoked_session_access.status_code == 401

    remaining_sessions = client.get(
        "/auth/sessions",
        headers=auth_headers(first_login["access_token"]),
    )
    assert remaining_sessions.status_code == 200
    assert len(remaining_sessions.json()) == 1


def test_profile_update_and_contact_change_endpoints(client, db_session: Session):
    user = create_verified_user(client, db_session, email="profile@test.trafficsms.com")
    tokens = login(client, email=user.email).json()

    profile_response = client.patch(
        "/users/me",
        headers=auth_headers(tokens["access_token"]),
        json={
            "home_location": "Corona, CA",
            "work_location": "Anaheim, CA",
            "gym_location": "Riverside, CA",
            "school_location": "Fullerton, CA",
            "default_state": "ca",
            "default_country": "us",
        },
    )
    assert profile_response.status_code == 200
    profile_body = profile_response.json()
    assert profile_body["home_location"] == "Corona, CA"
    assert profile_body["default_state"] == "CA"
    assert profile_body["default_country"] == "US"

    phone_response = client.post(
        "/users/me/change-phone",
        headers=auth_headers(tokens["access_token"]),
        json={
            "phone_number": "+17145559876",
            "current_password": "SecurePass1!",
        },
    )
    assert phone_response.status_code == 200
    assert phone_response.json()["phone_e164"] == "+17145559876"
    assert phone_response.json()["phone_verified"] is False

    email_change_request = client.post(
        "/users/me/change-email",
        headers=auth_headers(tokens["access_token"]),
        json={
            "new_email": "updated@test.trafficsms.com",
            "current_password": "SecurePass1!",
        },
    )
    assert email_change_request.status_code == 200

    db_session.refresh(user)
    assert user.pending_email == "updated@test.trafficsms.com"
    assert user.pending_email_verification_token is not None

    confirm_response = client.post(
        "/auth/confirm-email-change",
        json={"token": user.pending_email_verification_token},
    )
    assert confirm_response.status_code == 200

    db_session.refresh(user)
    assert user.email == "updated@test.trafficsms.com"
    assert user.pending_email is None


def test_change_password_revokes_current_session_and_requires_new_login(client, db_session: Session):
    user = create_verified_user(client, db_session, email="passwordchange@test.trafficsms.com")
    tokens = login(client, email=user.email).json()

    response = client.post(
        "/users/me/change-password",
        headers=auth_headers(tokens["access_token"]),
        json={
            "current_password": "SecurePass1!",
            "new_password": "EvenBetter3!",
        },
    )
    assert response.status_code == 200

    current_access = client.get(
        "/users/me",
        headers=auth_headers(tokens["access_token"]),
    )
    assert current_access.status_code == 401

    old_password_login = client.post(
        "/auth/login",
        json={"email": user.email, "password": "SecurePass1!", "remember_me": True},
    )
    new_password_login = client.post(
        "/auth/login",
        json={"email": user.email, "password": "EvenBetter3!", "remember_me": True},
    )

    assert old_password_login.status_code == 401
    assert new_password_login.status_code == 200

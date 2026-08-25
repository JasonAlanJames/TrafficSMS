from app.core.config import Settings
from app.services.email import SmtpEmailService


def email_settings() -> Settings:
    return Settings(
        DATABASE_URL="sqlite:///./trafficsms-email-tests.db",
        EMAIL_ENABLED=True,
        FRONTEND_URL="https://trafficsms.test",
        MAIL_FROM="noreply@trafficsms.test",
        MAIL_FROM_NAME="TrafficSMS",
        EMAIL_REPLY_TO="support@trafficsms.test",
        SMTP_HOST="smtp.trafficsms.test",
        SMTP_PORT=2525,
        SMTP_TLS=True,
        SMTP_SSL=False,
    )


def test_active_verification_email_uses_customer_facing_frontend_link() -> None:
    content = SmtpEmailService(email_settings())._build_verification_email(
        recipient="verify@trafficsms.local",
        token="safe-token",
        requested_again=False,
    )

    assert "https://trafficsms.test/verify-email?token=safe-token" in content.text_body
    assert "Verify account" in content.html_body
    assert "/api/auth/verify-email" not in content.text_body
    assert "/api/auth/verify-email" not in content.html_body


def test_active_password_reset_email_uses_customer_facing_frontend_link() -> None:
    content = SmtpEmailService(email_settings())._build_password_reset_email(
        recipient="reset@trafficsms.local",
        token="safe-token",
    )

    assert "https://trafficsms.test/reset-password?token=safe-token" in content.text_body
    assert "Reset password" in content.html_body
    assert "/api/auth/reset-password" not in content.text_body
    assert "/api/auth/reset-password" not in content.html_body
    assert "This link expires" in content.text_body
    assert "This link expires" in content.html_body
    assert "This token expires" not in content.text_body
    assert "This token expires" not in content.html_body
    for forbidden_copy in (
        "API client",
        "Reset token",
        "Reset endpoint",
        "Use the token below",
        "existing password reset flow",
    ):
        assert forbidden_copy not in content.text_body
        assert forbidden_copy not in content.html_body

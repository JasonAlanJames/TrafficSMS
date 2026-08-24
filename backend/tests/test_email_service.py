from app.core.config import settings
from app.email.service import EmailService, FakeEmailTransport, SMTPEmailTransport


def test_fake_transport_captures_lifecycle_email_without_network(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "frontend_url", "https://trafficsms.test")
    transport = FakeEmailTransport()
    result = EmailService(settings, transport).send_verification_email(
        recipient="verify@test.trafficsms.com", token="safe-token"
    )
    assert result.sent is True
    assert len(transport.messages) == 1
    assert "https://trafficsms.test/verify-email?token=safe-token" in transport.messages[0].text_body


def test_disabled_and_failed_email_delivery_are_safe(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_enabled", False)
    transport = FakeEmailTransport()
    assert EmailService(settings, transport).send_password_reset_email(
        recipient="reset@test.trafficsms.com", token="safe-token"
    ).reason == "disabled"
    monkeypatch.setattr(settings, "email_enabled", True)
    assert EmailService(settings, FakeEmailTransport(fail=True)).send_password_reset_email(
        recipient="reset@test.trafficsms.com", token="safe-token"
    ).reason == "delivery_failed"


def test_templates_use_safe_links_and_support_copy(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "frontend_url", "https://trafficsms.test")
    message = FakeEmailTransport()
    EmailService(settings, message).send_email_change_verification_email(
        recipient="pending@test.trafficsms.com", token="token with spaces"
    )
    rendered = message.messages[0]
    assert "TrafficSMS" in rendered.html_body
    assert "https://trafficsms.test/verify-email-change?token=token%20with%20spaces" in rendered.text_body
    assert settings.support_url in rendered.text_body
    assert "ignore this email" in rendered.text_body


def test_smtp_transport_rejects_missing_configuration(monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_host", "")
    assert SMTPEmailTransport(settings).is_configured is False

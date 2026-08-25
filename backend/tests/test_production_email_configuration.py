from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.email import SmtpEmailService


def settings_for_environment(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "APP_ENV": "production",
        "DATABASE_URL": "sqlite:///./trafficsms-config-tests.db",
        "SECRET_KEY": "a" * 32,
        "MAIL_FROM": "noreply@trafficsms.com",
        "MAIL_FROM_NAME": "TrafficSMS",
        "EMAIL_REPLY_TO": "support@trafficsms.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_mail_from_configuration_is_used_for_sender_and_reply_to_only() -> None:
    configured = settings_for_environment()
    service = SmtpEmailService(configured)
    message = service._build_message(
        service._build_password_reset_email(
            recipient="customer@trafficsms.local",
            token="safe-token",
        )
    )

    assert configured.mail_from == "noreply@trafficsms.com"
    assert configured.mail_from_name == "TrafficSMS"
    assert configured.email_reply_to == "support@trafficsms.com"
    assert message["From"] == "TrafficSMS <noreply@trafficsms.com>"
    assert message["Reply-To"] == "support@trafficsms.com"


def test_production_secret_key_must_be_at_least_32_characters() -> None:
    secret = "too-short-secret"
    dummy_smtp_secret = "DUMMY_SMTP_PASSWORD_MARKER"
    dummy_stripe_secret = "sk_test_DUMMY_MARKER"

    with pytest.raises(ValidationError) as exc_info:
        settings_for_environment(
            SECRET_KEY=secret,
            SMTP_PASSWORD=dummy_smtp_secret,
            STRIPE_SECRET_KEY=dummy_stripe_secret,
        )

    error_text = str(exc_info.value)

    assert "SECRET_KEY must be at least 32 characters" in error_text
    assert secret not in error_text
    assert dummy_smtp_secret not in error_text
    assert dummy_stripe_secret not in error_text

    assert settings_for_environment(
        SECRET_KEY="a" * 32
    ).secret_key == "a" * 32


def test_timestamp_defaults_migration_is_linked_without_recreating_users_table() -> None:
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "app/database/migrations/versions/c9f3a5d7e824_users_timestamp_defaults.py"
    )
    migration = migration_path.read_text(encoding="utf-8")

    assert 'down_revision: Union[str, Sequence[str], None] = "b8e2f4a6c713"' in migration
    assert "UPDATE users SET created_at = now()" in migration
    assert "UPDATE users SET updated_at = now()" in migration
    assert 'op.alter_column("users", "created_at", server_default=sa.text("now()"))' in migration
    assert 'op.alter_column("users", "updated_at", server_default=sa.text("now()"))' in migration
    assert "create_table" not in migration
    assert "drop_table" not in migration

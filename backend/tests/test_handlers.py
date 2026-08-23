"""Unit tests for primary SMS command handlers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

from sqlalchemy.orm import Session

from app.models.entities import User
from app.sms.handlers.help import handle_help
from app.sms.handlers.start import handle_start
from app.sms.handlers.stop import handle_stop
from app.sms.handlers.traffic import handle_traffic
from app.sms.handlers.unknown import handle_unknown
from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext
from app.sms.parser import SMSParser
from app.sms.formatter import format_sms_response
from app.sms.models import SMSResponse


def _context(
    db: object | None = None,
    intent: SMSIntent | None = None,
) -> SMSMessageContext:
    return SMSMessageContext(
        db=cast(Session, db or object()),
        from_number="+17145550123",
        intent=intent,
    )


def test_help_handler_returns_command_reference() -> None:
    """HELP exposes the stable public command list."""

    response = asyncio.run(handle_help(SMSParser().parse("HELP"), _context()))

    assert response.success is True
    assert response.intent is SMSIntent.HELP
    assert "Available Commands:" in response.message
    assert response.metadata == {}


def test_start_and_stop_handlers_return_compliance_messages() -> None:
    """START and STOP retain their expected Twilio-facing responses."""

    start = asyncio.run(handle_start(SMSParser().parse("START"), _context()))
    stop = asyncio.run(handle_stop(SMSParser().parse("STOP"), _context()))

    assert start.success is True
    assert start.intent is SMSIntent.START
    assert "Welcome back" in start.message
    assert stop.success is True
    assert stop.intent is SMSIntent.STOP
    assert "unsubscribed" in stop.message


def test_unknown_handler_returns_safe_fallback() -> None:
    """Unknown commands never leak internal details."""

    response = asyncio.run(
        handle_unknown(SMSParser().parse("nonsense"), _context())
    )

    assert response.success is False
    assert response.intent is SMSIntent.UNKNOWN
    assert response.message == (
        "Sorry, I didn't understand that command.\n\n"
        "Reply HELP for available commands."
    )


def test_formatter_normalizes_spacing_and_bounds_messages() -> None:
    """The presentation layer owns outbound whitespace and length limits."""

    response = SMSResponse(
        success=True,
        intent=SMSIntent.HELP,
        message="First\r\n\r\n\r\nSecond",
    )

    assert format_sms_response(response) == "First\n\nSecond"
    assert format_sms_response(response, maximum_length=3) == "Fir"


def test_webhook_uses_sms_engine_and_returns_twiml(client, monkeypatch) -> None:
    """The route delegates inbound commands to the SMS engine."""

    monkeypatch.setattr(
        "app.api.twilio_webhook.get_settings",
        lambda: SimpleNamespace(
            app_env="development",
            twilio_auth_token="test-token",
            public_base_url="https://trafficsms.example",
        ),
    )

    response = client.post(
        "/webhooks/twilio/inbound",
        data={"From": "+17145550123", "Body": "help"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "Available Commands:" in response.text


def test_traffic_handler_bridges_to_existing_engine(monkeypatch) -> None:
    """TRAFFIC authorizes and accounts before invoking the existing engine."""

    user = User(
        id=1,
        email="driver@example.com",
        phone_e164="+17145550123",
        subscription_plan="standard",
        subscription_status="active",
    )

    class FakeDatabase:
        def scalar(self, _query):
            return user

    class FakeBillingService:
        def __init__(self, _repository):
            self.context = SimpleNamespace(
                subscription=SimpleNamespace(plan="standard")
            )

        def ensure_active_subscription(self, _user):
            return self.context

        def record_sms_usage(self, _user):
            return SimpleNamespace(remaining_sms=59)

    async def fake_build_traffic_reply(**kwargs):
        assert kwargs["request"].mode == "area"
        assert kwargs["request"].area == "CORONA"
        assert kwargs["user"] is user
        return "Corona traffic is moving normally."

    monkeypatch.setattr(
        "app.sms.handlers.traffic.BillingService",
        FakeBillingService,
    )
    monkeypatch.setattr(
        "app.sms.handlers.traffic.build_traffic_reply",
        fake_build_traffic_reply,
    )

    response = asyncio.run(
        handle_traffic(
            SMSParser().parse("traffic corona"),
            _context(FakeDatabase(), SMSIntent.TRAFFIC_ROUTE),
        )
    )

    assert response.success is True
    assert response.intent is SMSIntent.TRAFFIC_ROUTE
    assert response.metadata == {
        "remaining_queries": 59,
        "subscription_level": "standard",
    }
    assert response.message.endswith("SMS remaining this period: 59")

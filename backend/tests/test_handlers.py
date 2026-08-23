"""Unit tests for primary SMS command handlers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_request import TrafficRequest
from app.services.traffic_service import TrafficPreparation, TrafficServiceResult
from app.sms.context import SMSContext
from app.sms.handlers.help import handle_help
from app.sms.handlers.start import handle_start
from app.sms.handlers.stop import handle_stop
from app.sms.handlers.traffic import handle_traffic
from app.sms.handlers.unknown import handle_unknown
from app.sms.intents import SMSIntent
from app.sms.formatter import format_sms_response
from app.sms.models import SMSResponse


def _context(
    db: object | None = None,
    user: User | None = None,
    intent: SMSIntent | None = None,
) -> SMSContext:
    return SMSContext(
        db=cast(Session, db or object()),
        phone_number="+17145550123",
        user=user,
        subscription=None,
        normalized_text="TRAFFIC CORONA",
        raw_text="traffic corona",
        tokens=("TRAFFIC", "CORONA"),
        parsed_arguments=("CORONA",),
        timestamp=datetime.now(UTC),
        intent=intent,
    )


def test_help_handler_returns_command_reference() -> None:
    """HELP exposes the stable public command list."""

    response = asyncio.run(handle_help(_context()))

    assert response.success is True
    assert response.intent is SMSIntent.HELP
    assert "Available Commands:" in response.message
    assert response.metadata == {}


def test_start_and_stop_handlers_return_compliance_messages() -> None:
    """START and STOP retain their expected Twilio-facing responses."""

    start = asyncio.run(handle_start(_context()))
    stop = asyncio.run(handle_stop(_context()))

    assert start.success is True
    assert start.intent is SMSIntent.START
    assert "Welcome back" in start.message
    assert stop.success is True
    assert stop.intent is SMSIntent.STOP
    assert "unsubscribed" in stop.message


def test_unknown_handler_returns_safe_fallback() -> None:
    """Unknown commands never leak internal details."""

    response = asyncio.run(handle_unknown(_context()))

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

    class FakeBillingService:
        def __init__(self, _repository):
            self.context = SimpleNamespace(
                subscription=SimpleNamespace(plan="standard")
            )

        def ensure_active_subscription(self, _user):
            return self.context

        def record_sms_usage(self, _user):
            return SimpleNamespace(remaining_sms=59)

    class FakeTrafficService:
        def prepare_request(self, context: SMSContext) -> TrafficPreparation:
            assert context.user is user
            return TrafficPreparation(
                request=TrafficRequest(
                    mode="area",
                    area="CORONA",
                    subscriber_id=user.id,
                )
            )

        async def build_reply(
            self,
            context: SMSContext,
            request: TrafficRequest,
        ) -> TrafficServiceResult:
            assert context.user is user
            assert request.mode == "area"
            assert request.area == "CORONA"
            return TrafficServiceResult(
                message="Corona traffic is moving normally.",
                request=request,
                metadata={"traffic_mode": "area"},
            )

    monkeypatch.setattr(
        "app.sms.handlers.traffic.BillingService",
        FakeBillingService,
    )
    monkeypatch.setattr(
        "app.sms.handlers.traffic.TrafficService",
        FakeTrafficService,
    )

    response = asyncio.run(
        handle_traffic(
            _context(user=user, intent=SMSIntent.TRAFFIC_ROUTE),
        )
    )

    assert response.success is True
    assert response.intent is SMSIntent.TRAFFIC_ROUTE
    assert response.metadata == {
        "traffic_mode": "area",
        "remaining_queries": 59,
        "subscription_level": "standard",
    }
    assert response.message.endswith("SMS remaining this period: 59")

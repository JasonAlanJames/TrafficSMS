"""Saved-route SMS command coverage through the existing command primitives."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from app.models.entities import User
from app.services.traffic_service import TrafficServiceResult
from app.sms.context import SMSContext
from app.sms.handlers.route import handle_delete_route, handle_list_routes, handle_save_route
from app.sms.handlers.traffic import handle_traffic
from app.sms.intent_resolver import SMSIntentResolver
from app.sms.intents import SMSIntent
from app.sms.parser import SMSParser


def _context(db, user: User, text: str, intent: SMSIntent | None = None) -> SMSContext:
    parsed = SMSParser().parse(text)
    return SMSContext(
        db=db, phone_number=user.phone_e164 or "+17145550123", user=user,
        subscription=None, normalized_text=parsed.normalized_text, raw_text=text,
        tokens=parsed.tokens, parsed_arguments=parsed.arguments, timestamp=datetime.now(UTC), intent=intent,
    )


def test_saved_route_sms_management_and_alias_resolution(db_session) -> None:
    user = User(email="sms.routes@trafficsms.local", phone_e164="+17145550123")
    db_session.add(user)
    db_session.commit()

    saved = asyncio.run(handle_save_route(_context(
        db_session, user, "SAVE ROUTE WORK 92882 TO IRVINE", SMSIntent.SAVE_ROUTE,
    )))
    assert saved.success is True
    assert "WORK" in saved.message

    for command, expected_intent in (
        ("SAVE ROUTE WORK 92882 TO IRVINE", SMSIntent.SAVE_ROUTE),
        ("LIST ROUTES", SMSIntent.LIST_ROUTES),
        ("DELETE ROUTE WORK", SMSIntent.DELETE_ROUTE),
    ):
        resolved = _context(db_session, user, command)
        assert asyncio.run(SMSIntentResolver().resolve(resolved)) is expected_intent

    listed = asyncio.run(handle_list_routes(_context(db_session, user, "LIST ROUTES", SMSIntent.LIST_ROUTES)))
    assert listed.success is True
    assert "92882 to IRVINE" in listed.message

    context = _context(db_session, user, "TRAFFIC WORK")
    assert asyncio.run(SMSIntentResolver().resolve(context)) is SMSIntent.TRAFFIC_WORK
    explicit = _context(db_session, user, "ROUTE WORK")
    assert asyncio.run(SMSIntentResolver().resolve(explicit)) is SMSIntent.TRAFFIC_SAVED_ROUTE

    deleted = asyncio.run(handle_delete_route(_context(
        db_session, user, "DELETE ROUTE WORK", SMSIntent.DELETE_ROUTE,
    )))
    assert deleted.success is True
    missing = asyncio.run(handle_delete_route(_context(
        db_session, user, "DELETE ROUTE WORK", SMSIntent.DELETE_ROUTE,
    )))
    assert missing.success is False


def test_saved_route_sms_traffic_uses_existing_traffic_handler(db_session, monkeypatch) -> None:
    user = User(
        email="sms.traffic@trafficsms.local", phone_e164="+17145550124",
        subscription_plan="standard", subscription_status="active",
    )
    db_session.add(user)
    db_session.commit()
    asyncio.run(handle_save_route(_context(
        db_session, user, "SAVE ROUTE LAX CORONA TO LAX", SMSIntent.SAVE_ROUTE,
    )))

    class FakeBillingService:
        def __init__(self, _repository):
            self.context = SimpleNamespace(subscription=SimpleNamespace(plan="standard"))

        def ensure_active_subscription(self, _user):
            return self.context

        def record_sms_usage(self, _user):
            return SimpleNamespace(remaining_sms=59)

    class FakeTrafficService:
        async def build_reply(self, _context, request):
            assert request.origin == "CORONA"
            assert request.destination == "LAX"
            return TrafficServiceResult(message="Route traffic is clear.", request=request, metadata={"traffic_mode": "route"})

    monkeypatch.setattr("app.sms.handlers.traffic.BillingService", FakeBillingService)
    monkeypatch.setattr("app.sms.handlers.traffic.TrafficService", FakeTrafficService)
    response = asyncio.run(handle_traffic(_context(db_session, user, "TRAFFIC ROUTE LAX", SMSIntent.TRAFFIC_SAVED_ROUTE)))
    assert response.success is True
    assert response.metadata["saved_route_alias"] == "LAX"

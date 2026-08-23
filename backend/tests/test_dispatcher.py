"""Unit tests for SMS intent detection and handler dispatch."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.orm import Session

from app.sms.context import SMSContext
from app.sms.dispatcher import SMSDispatcher
from app.sms.intents import SMSIntent
from app.sms.models import SMSResponse


def _context() -> SMSContext:
    return SMSContext(
        db=cast(Session, object()),
        phone_number="+17145550123",
        user=None,
        subscription=None,
        normalized_text="TRAFFIC HOME",
        raw_text="traffic home",
        tokens=("TRAFFIC", "HOME"),
        parsed_arguments=("HOME",),
        timestamp=datetime.now(UTC),
    )


def test_dispatcher_calls_only_the_resolved_handler() -> None:
    """The selected handler determines the response returned to the caller."""

    called: list[SMSIntent] = []

    def handler_for(intent: SMSIntent):
        async def handler(
            _: SMSContext,
        ) -> SMSResponse:
            called.append(intent)
            return SMSResponse(True, intent, f"handled {intent.value}")

        return handler

    handlers = {intent: handler_for(intent) for intent in SMSIntent}
    dispatcher = SMSDispatcher(handlers=handlers)
    context = _context()

    response = asyncio.run(dispatcher.dispatch(SMSIntent.TRAFFIC_HOME, context))

    assert called == [SMSIntent.TRAFFIC_HOME]
    assert response.intent is SMSIntent.TRAFFIC_HOME
    assert response.message == "handled traffic_home"

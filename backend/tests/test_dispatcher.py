"""Unit tests for SMS intent detection and handler dispatch."""

from __future__ import annotations

import asyncio
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.sms.dispatcher import SMSDispatcher
from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext, SMSParseResult, SMSResponse
from app.sms.parser import SMSParser


@pytest.mark.parametrize(
    ("message", "intent"),
    [
        ("HELP", SMSIntent.HELP),
        ("START", SMSIntent.START),
        ("STOP", SMSIntent.STOP),
        ("TRAFFIC", SMSIntent.TRAFFIC),
        ("TRAFFIC HOME", SMSIntent.TRAFFIC_HOME),
        ("TRAFFIC WORK", SMSIntent.TRAFFIC_WORK),
        ("TRAFFIC GYM", SMSIntent.TRAFFIC_GYM),
        ("TRAFFIC SCHOOL", SMSIntent.TRAFFIC_SCHOOL),
        ("TRAFFIC I15 NORTH", SMSIntent.TRAFFIC_ROUTE),
        ("something else", SMSIntent.UNKNOWN),
    ],
)
def test_dispatcher_resolves_expected_intent(
    message: str,
    intent: SMSIntent,
) -> None:
    """Routing decisions are centralized in the dispatcher."""

    parsed = SMSParser().parse(message)

    assert SMSDispatcher.resolve_intent(parsed) is intent


def test_dispatcher_calls_only_the_resolved_handler() -> None:
    """The selected handler determines the response returned to the caller."""

    called: list[SMSIntent] = []

    def handler_for(intent: SMSIntent):
        async def handler(
            _: SMSParseResult,
            __: SMSMessageContext,
        ) -> SMSResponse:
            called.append(intent)
            return SMSResponse(True, intent, f"handled {intent.value}")

        return handler

    handlers = {intent: handler_for(intent) for intent in SMSIntent}
    dispatcher = SMSDispatcher(handlers=handlers)
    parsed = SMSParser().parse("traffic home")
    context = SMSMessageContext(
        db=cast(Session, object()),
        from_number="+17145550123",
    )

    response = asyncio.run(dispatcher.dispatch(parsed, context))

    assert called == [SMSIntent.TRAFFIC_HOME]
    assert response.intent is SMSIntent.TRAFFIC_HOME
    assert response.message == "handled traffic_home"

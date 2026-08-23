"""Unit tests for deterministic SMS intent resolution."""

import pytest

from app.sms.intent_resolver import SMSIntentResolver
from app.sms.intents import SMSIntent
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
        ("TRAFFIC HOME TO WORK", SMSIntent.TRAFFIC_ROUTE),
        ("P42 YES", SMSIntent.POLICE_VOTE),
        ("something else", None),
    ],
)
def test_intent_resolver_returns_expected_intent(
    message: str,
    intent: SMSIntent | None,
) -> None:
    """All command routing is owned by the intent resolver."""

    parsed = SMSParser().parse(message)

    assert SMSIntentResolver().resolve_deterministic(parsed) is intent

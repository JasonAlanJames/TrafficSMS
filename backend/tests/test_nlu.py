"""Revision 2B tests for deterministic-first conversational SMS resolution."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.models.entities import User
from app.sms.context import SMSContext
from app.sms.conversation import SMSConversationMemory
from app.sms.intent_resolver import SMSIntentResolver
from app.sms.intents import SMSIntent
from app.sms.parser import SMSParser
from app.sms.providers.provider import AIIntentResult, LLMIntentProvider


def _context(
    message: str,
    *,
    phone_number: str = "+17145550123",
    user: User | None = None,
    timestamp: datetime | None = None,
) -> SMSContext:
    parsed = SMSParser().parse(message)
    return SMSContext(
        db=cast(Session, object()),
        phone_number=phone_number,
        user=user,
        subscription=None,
        normalized_text=parsed.normalized_text,
        raw_text=parsed.raw_text,
        tokens=parsed.tokens,
        parsed_arguments=parsed.arguments,
        timestamp=timestamp or datetime.now(UTC),
    )


class RecordingProvider(LLMIntentProvider):
    """Controllable provider used to verify resolver fallback policy."""

    def __init__(self, result: AIIntentResult):
        self.result = result
        self.calls = 0

    async def resolve(self, context: SMSContext) -> AIIntentResult:
        self.calls += 1
        return self.result


@pytest.mark.parametrize(
    ("message", "canonical", "intent", "entity"),
    [
        ("TRAFFIC THE 91 WEST", "TRAFFIC SR-91 WEST", SMSIntent.TRAFFIC_ROUTE, "SR-91"),
        ("TRAFFIC RIVERSIDE FREEWAY", "TRAFFIC SR-91", SMSIntent.TRAFFIC_ROUTE, "SR-91"),
        ("TRAFFIC 405 SOUTH", "TRAFFIC I-405 SOUTH", SMSIntent.TRAFFIC_ROUTE, "I-405"),
        ("TRAFFIC 5 FREEWAY", "TRAFFIC I-5", SMSIntent.TRAFFIC_ROUTE, "I-5"),
        (
            "TRAFFIC LAX",
            "TRAFFIC LOS ANGELES INTERNATIONAL AIRPORT",
            SMSIntent.TRAFFIC_ROUTE,
            "LOS ANGELES INTERNATIONAL AIRPORT",
        ),
        ("TRAFFIC DISNEY", "TRAFFIC DISNEYLAND", SMSIntent.TRAFFIC_ROUTE, "DISNEYLAND"),
    ],
)
def test_deterministic_synonyms_resolve_without_provider(
    message: str,
    canonical: str,
    intent: SMSIntent,
    entity: str,
) -> None:
    """Known freeway and landmark aliases never need an AI provider."""

    provider = RecordingProvider(AIIntentResult(0.0, None))
    context = _context(message)

    resolved = asyncio.run(SMSIntentResolver(provider=provider).resolve(context))

    assert resolved is intent
    assert context.resolved_text == canonical
    assert context.metadata["intent_source"] == "deterministic"
    assert provider.calls == 0
    assert entity in context.entities.values()


def test_ai_fallback_maps_conversational_area_request() -> None:
    """A high-confidence provider candidate becomes a canonical traffic command."""

    context = _context("What's traffic like near Corona?")

    intent = asyncio.run(SMSIntentResolver().resolve(context))

    assert intent is SMSIntent.TRAFFIC_ROUTE
    assert context.resolved_text == "TRAFFIC CORONA"
    assert context.entities["city"] == "CORONA"
    assert context.metadata["intent_source"] == "ai"
    assert context.ai_result is not None
    assert context.ai_result.parser_fallback is True


def test_ai_fallback_uses_saved_home_for_destination_request() -> None:
    """Natural language maps to an existing saved-location route command."""

    user = User(
        id=1,
        email="driver@example.com",
        phone_e164="+17145550123",
        home_location="Corona, CA",
    )
    context = _context("How's traffic to LAX?", user=user)

    intent = asyncio.run(SMSIntentResolver().resolve(context))

    assert intent is SMSIntent.TRAFFIC_ROUTE
    assert context.resolved_text == (
        "TRAFFIC HOME TO LOS ANGELES INTERNATIONAL AIRPORT"
    )
    assert context.entities["origin"] == "HOME"
    assert context.entities["destination"] == "LOS ANGELES INTERNATIONAL AIRPORT"


@pytest.mark.parametrize(
    ("message", "canonical_command", "expected_intent"),
    [
        ("Is the 91 backed up?", "TRAFFIC SR-91", SMSIntent.TRAFFIC_ROUTE),
        ("How long will it take to get home?", "TRAFFIC HOME", SMSIntent.TRAFFIC_HOME),
        ("How's traffic going to work?", "TRAFFIC WORK", SMSIntent.TRAFFIC_WORK),
        ("Any accidents on I-15?", "TRAFFIC I-15", SMSIntent.TRAFFIC_ROUTE),
        ("Is Disneyland busy?", "TRAFFIC DISNEYLAND", SMSIntent.TRAFFIC_ROUTE),
        (
            "Traffic from Corona to Irvine.",
            "TRAFFIC CORONA TO IRVINE",
            SMSIntent.TRAFFIC_ROUTE,
        ),
    ],
)
def test_mock_provider_maps_supported_conversational_requests(
    message: str,
    canonical_command: str,
    expected_intent: SMSIntent,
) -> None:
    """Conversational traffic requests become existing deterministic commands."""

    context = _context(message)

    intent = asyncio.run(SMSIntentResolver().resolve(context))

    assert intent is expected_intent
    assert context.resolved_text == canonical_command
    assert context.metadata["intent_source"] == "ai"


def test_low_confidence_provider_result_is_rejected() -> None:
    """The resolver returns UNKNOWN rather than accepting a weak AI guess."""

    provider = RecordingProvider(
        AIIntentResult(
            confidence=0.60,
            detected_intent=SMSIntent.TRAFFIC_ROUTE,
            command_text="TRAFFIC CORONA",
            entities={"city": "CORONA"},
            reasoning="Deliberately below threshold.",
        )
    )
    context = _context("Could you maybe help with something?")

    intent = asyncio.run(
        SMSIntentResolver(provider=provider, confidence_threshold=0.85).resolve(
            context
        )
    )

    assert intent is SMSIntent.UNKNOWN
    assert context.metadata["intent_source"] == "unknown"
    assert context.metadata["ai_confidence"] == 0.60
    assert provider.calls == 1


def test_custom_provider_is_replaceable_without_resolver_changes() -> None:
    """Any provider implementing the contract can supply canonical candidates."""

    provider = RecordingProvider(
        AIIntentResult(
            confidence=0.99,
            detected_intent=SMSIntent.TRAFFIC_ROUTE,
            command_text="TRAFFIC CORONA TO IRVINE",
            entities={"origin": "CORONA", "destination": "IRVINE"},
            reasoning="Custom provider test.",
        )
    )
    context = _context("A custom natural language phrase")

    intent = asyncio.run(SMSIntentResolver(provider=provider).resolve(context))

    assert intent is SMSIntent.TRAFFIC_ROUTE
    assert context.resolved_text == "TRAFFIC CORONA TO IRVINE"
    assert context.entities["route"] == "CORONA TO IRVINE"
    assert provider.calls == 1


def test_direction_follow_up_uses_expiring_conversation_memory() -> None:
    """A short direction message completes the previous highway request."""

    memory = SMSConversationMemory(ttl_seconds=60)
    resolver = SMSIntentResolver(conversation_memory=memory)
    started_at = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)

    first = _context("TRAFFIC I15", timestamp=started_at)
    assert asyncio.run(resolver.resolve(first)) is SMSIntent.TRAFFIC_ROUTE

    follow_up = _context(
        "northbound?",
        timestamp=started_at + timedelta(seconds=30),
    )
    intent = asyncio.run(resolver.resolve(follow_up))

    assert intent is SMSIntent.TRAFFIC_ROUTE
    assert follow_up.resolved_text == "TRAFFIC I-15 NORTH"
    assert follow_up.metadata["intent_source"] == "conversation"
    assert follow_up.entities == {
        "highway": "I-15",
        "corridor": "I-15",
        "direction": "NORTH",
    }


def test_route_origin_follow_up_uses_pending_destination_memory() -> None:
    """An incomplete destination request is completed by a later origin message."""

    memory = SMSConversationMemory(ttl_seconds=60)
    resolver = SMSIntentResolver(conversation_memory=memory)
    started_at = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)

    pending = _context("Traffic to LAX", timestamp=started_at)
    assert asyncio.run(resolver.resolve(pending)) is SMSIntent.UNKNOWN

    follow_up = _context(
        "From Corona",
        timestamp=started_at + timedelta(seconds=30),
    )
    intent = asyncio.run(resolver.resolve(follow_up))

    assert intent is SMSIntent.TRAFFIC_ROUTE
    assert follow_up.resolved_text == (
        "TRAFFIC CORONA TO LOS ANGELES INTERNATIONAL AIRPORT"
    )
    assert follow_up.entities["origin"] == "CORONA"
    assert follow_up.entities["destination"] == "LOS ANGELES INTERNATIONAL AIRPORT"


def test_expired_conversation_state_is_not_used() -> None:
    """Expired memory cannot cause a stale follow-up to be interpreted."""

    memory = SMSConversationMemory(ttl_seconds=60)
    resolver = SMSIntentResolver(conversation_memory=memory)
    started_at = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)

    assert asyncio.run(
        resolver.resolve(_context("TRAFFIC I15", timestamp=started_at))
    ) is SMSIntent.TRAFFIC_ROUTE
    expired_follow_up = _context(
        "NORTHBOUND",
        timestamp=started_at + timedelta(seconds=61),
    )

    assert asyncio.run(resolver.resolve(expired_follow_up)) is SMSIntent.UNKNOWN
    assert expired_follow_up.metadata["intent_source"] == "unknown"

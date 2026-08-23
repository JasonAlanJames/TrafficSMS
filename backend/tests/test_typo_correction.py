"""Revision 3.1 tests for isolated deterministic command typo correction."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.sms.context import SMSContext
from app.sms.intent_resolver import SMSIntentResolver
from app.sms.intents import SMSIntent
from app.sms.handlers.unknown import handle_unknown
from app.sms.providers.provider import AIIntentResult, LLMIntentProvider
from app.sms.typo_correction import (
    TypoCorrectionService,
    damerau_levenshtein_distance,
)


def _context(message: str) -> SMSContext:
    normalized_text = message.upper()
    tokens = tuple(normalized_text.split())
    return SMSContext(
        db=cast(Session, object()),
        phone_number="+17145550123",
        user=None,
        subscription=None,
        normalized_text=normalized_text,
        raw_text=message,
        tokens=tokens,
        parsed_arguments=tokens[1:],
        timestamp=datetime.now(UTC),
    )


class FailingProvider(LLMIntentProvider):
    """Provider guard that proves deterministic corrections never invoke AI."""

    async def resolve(self, context: SMSContext) -> AIIntentResult:
        raise AssertionError("AI provider must not run for deterministic typo correction")


@pytest.mark.parametrize(
    ("source", "target", "distance"),
    [
        ("CA", "AC", 1),
        ("TRAFIC", "TRAFFIC", 1),
        ("HELPP", "HELP", 1),
    ],
)
def test_damerau_levenshtein_distance(
    source: str,
    target: str,
    distance: int,
) -> None:
    """The service uses transposition-aware Damerau-Levenshtein distance."""

    assert damerau_levenshtein_distance(source, target) == distance


@pytest.mark.parametrize(
    ("message", "corrected"),
    [
        ("TRAFFFIC HOME", "TRAFFIC HOME"),
        ("TRAFIC HOME", "TRAFFIC HOME"),
        ("HELPP", "HELP"),
        ("STARRT", "START"),
        ("STOOP", "STOP"),
    ],
)
def test_high_confidence_command_typos_are_corrected(
    message: str,
    corrected: str,
) -> None:
    """Known command typos continue without requiring a user retry."""

    service = TypoCorrectionService(
        max_edit_distance=2,
        confidence_threshold=0.80,
    )
    result = service.correct(message)

    assert result.applied is True
    assert result.rejected is False
    assert result.corrected_text == corrected


def test_low_confidence_typo_is_rejected_without_guessing() -> None:
    """A configured confidence policy blocks ambiguous corrections."""

    service = TypoCorrectionService(
        max_edit_distance=2,
        confidence_threshold=0.95,
    )
    result = service.correct("TRAFIC HOME")

    assert result.applied is False
    assert result.rejected is True
    assert result.corrected_text == "TRAFIC HOME"


def test_resolver_uses_typo_correction_before_synonyms_and_ai() -> None:
    """A corrected traffic command resolves through the ordinary deterministic path."""

    context = _context("TRAFFFIC HOME")
    intent = asyncio.run(
        SMSIntentResolver(provider=FailingProvider()).resolve(context)
    )

    assert intent is SMSIntent.TRAFFIC_HOME
    assert context.resolved_text == "TRAFFIC HOME"
    assert context.metadata["intent_source"] == "deterministic"
    assert context.metadata["typo_corrected"]["from"] == "TRAFFFIC"


def test_low_confidence_typo_returns_unknown_before_ai() -> None:
    """Low-confidence spelling input does not fall through to optional AI."""

    resolver = SMSIntentResolver(
        provider=FailingProvider(),
        typo_correction_service=TypoCorrectionService(
            max_edit_distance=2,
            confidence_threshold=0.95,
        ),
    )
    context = _context("TRAFIC HOME")

    intent = asyncio.run(resolver.resolve(context))

    assert intent is SMSIntent.UNKNOWN
    assert context.metadata["typo_correction_rejected"] is True

    response = asyncio.run(handle_unknown(context))
    assert response.message == (
        "TrafficSMS\n\n"
        "Sorry, I couldn't understand your request.\n\n"
        "Please check your spelling and try again.\n\n"
        "Reply HELP for available commands."
    )

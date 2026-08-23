"""Tests for deterministic summary cleanup and one-message delivery decisions."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from app.llm.delivery_formatter import DeliveryFormatter
from app.llm.summary_formatter import SummaryFormatter
from app.llm.traffic_summary_service import TrafficSummaryService
from app.models.traffic_report import AlternateRoute, TrafficReport
from app.models.traffic_summary_request import (
    TrafficSummaryAlternateRoute,
    TrafficSummaryRequest,
)


def _request() -> TrafficSummaryRequest:
    return TrafficSummaryRequest(
        location="Corona -> Anaheim",
        travel_time=42,
        normal_travel_time=30,
        delay_minutes=12,
        congestion_level="HIGH",
        severity="HIGH",
        incidents=(),
        alternate_routes=(
            TrafficSummaryAlternateRoute("SR-60", 33, 9),
        ),
        confidence=1.0,
        provenance=(),
        report_age=None,
        generated_timestamp=datetime(2026, 8, 23, tzinfo=UTC),
    )


def test_summary_formatter_normalizes_a_grounded_bedrock_summary() -> None:
    """Useful model text is cleaned without changing its supplied facts."""

    summary = SummaryFormatter().format(
        "Traffic Summary: Corona -> Anaheim has HIGH traffic: 42 min with 12 min delay. SR-60 is available!!!",
        _request(),
    )

    assert summary == "Corona -> Anaheim has HIGH traffic: 42 min with 12 min delay. SR-60 is available!"


def test_summary_formatter_rejects_an_invented_travel_time() -> None:
    """Any unsupported critical value triggers deterministic fallback."""

    assert SummaryFormatter().format(
        "Corona -> Anaheim has HIGH traffic: 99 min with 12 min delay. SR-60 is available.",
        _request(),
    ) is None


def test_summary_formatter_rejects_an_extra_invented_number() -> None:
    """Repeating correct facts cannot hide an additional unsupported number."""

    assert SummaryFormatter().format(
        "Corona -> Anaheim has HIGH traffic: 42 min with 12 min delay and 99 incidents. SR-60 is available.",
        _request(),
    ) is None


def test_delivery_formatter_selects_single_sms_after_safe_compression() -> None:
    """A concise rewrite remains one SMS with measurable compression metadata."""

    settings = SimpleNamespace(
        sms_character_threshold=25,
        mms_character_threshold=1600,
        delivery_compression_threshold=320,
    )
    decision = DeliveryFormatter(settings=settings).prepare("TrafficSMS Travel: 42 minutes")

    assert decision.delivery_type == "SMS"
    assert decision.estimated_segments == 1
    assert decision.compression_applied is True
    assert decision.message == "Travel: 42 min"


def test_delivery_formatter_selects_one_mms_when_compression_would_not_fit_sms() -> None:
    """The formatter never returns a multi-segment SMS decision."""

    settings = SimpleNamespace(
        sms_character_threshold=20,
        mms_character_threshold=120,
        delivery_compression_threshold=320,
    )
    decision = DeliveryFormatter(settings=settings).prepare("X" * 80)

    assert decision.delivery_type == "MMS"
    assert decision.estimated_segments == 1
    assert decision.character_count == 80


def test_delivery_formatter_truncates_only_after_the_one_mms_limit() -> None:
    """An extreme response still produces exactly one bounded delivery payload."""

    settings = SimpleNamespace(
        sms_character_threshold=20,
        mms_character_threshold=40,
        delivery_compression_threshold=320,
    )
    decision = DeliveryFormatter(settings=settings).prepare("X" * 80)

    assert decision.delivery_type == "MMS"
    assert decision.estimated_segments == 1
    assert decision.truncation_applied is True
    assert decision.message.endswith("...")


def test_summary_service_falls_back_when_provider_fails() -> None:
    """Traffic delivery remains available when the optional provider is unavailable."""

    class FailingProvider:
        async def summarize(self, _request: TrafficSummaryRequest) -> str:
            raise TimeoutError("Bedrock unavailable")

    settings = SimpleNamespace(bedrock_enabled=True)
    report = TrafficReport(location="Corona", generated_at=datetime(2026, 8, 23, tzinfo=UTC))
    result = asyncio.run(
        TrafficSummaryService(settings=settings, provider=FailingProvider()).summarize(
            report,
            "Deterministic traffic update.",
        )
    )

    assert result == "Deterministic traffic update."


def test_summary_service_uses_only_the_sanitized_request_for_grounded_output() -> None:
    """The provider receives a request object rather than a report or service instance."""

    class GroundedProvider:
        def __init__(self) -> None:
            self.request: TrafficSummaryRequest | None = None

        async def summarize(self, request: TrafficSummaryRequest) -> str:
            self.request = request
            return "Corona has HIGH traffic: 42 min with 12 min delay."

    provider = GroundedProvider()
    settings = SimpleNamespace(bedrock_enabled=True)
    report = TrafficReport(
        location="Corona",
        travel_time=42,
        normal_travel_time=30,
        delay_minutes=12,
        congestion_level="HIGH",
        severity="HIGH",
        generated_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    result = asyncio.run(
        TrafficSummaryService(settings=settings, provider=provider).summarize(
            report,
            "Deterministic traffic update.",
        )
    )

    assert result == "Corona has HIGH traffic: 42 min with 12 min delay."
    assert isinstance(provider.request, TrafficSummaryRequest)

"""Milestone 4.1 telemetry, provenance, and delivery regression coverage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.llm.delivery_formatter import DeliveryFormatter
from app.models.summary_metadata import SummaryMetadata
from app.models.traffic_freshness import TrafficFreshness
from app.models.traffic_report import TrafficReport
from app.models.traffic_source import TrafficSource
from app.sms.formatter import format_traffic_report


def test_source_freshness_and_attribution_are_typed_report_facts() -> None:
    source = TrafficSource(
        source_name="State DOT", retrieved_at=datetime(2026, 8, 23, tzinfo=UTC),
        confidence=0.9, data_age=timedelta(seconds=45), coverage="CA",
        latency=timedelta(milliseconds=20), status="AVAILABLE",
        provider_name="Google Traffic", is_live=True, supports_routes=True,
        metadata=(("region", "CA"),),
    )
    report = TrafficReport(
        location="Corona", travel_time=42, delay_minutes=12,
        congestion_level="HIGH", severity="HIGH", sources=(source,),
        freshness=TrafficFreshness(newest_source_age=timedelta(seconds=45), is_live=True),
    )

    rendered = format_traffic_report(report)

    assert "Based on Google Traffic." in rendered
    assert rendered.endswith("Updated 45 seconds ago.")
    assert source.metadata == (("region", "CA"),)


def test_delivery_decision_copies_internal_summary_telemetry() -> None:
    settings = SimpleNamespace(
        sms_character_threshold=160, mms_character_threshold=1600,
        delivery_compression_threshold=320,
    )
    report = TrafficReport(
        location="Corona",
        summary_metadata=SummaryMetadata(
            summary_used=True, provider="Bedrock", model="test-model",
            summary_source="bedrock", generation_latency_ms=25,
        ),
    )

    decision = DeliveryFormatter(settings=settings).prepare("Traffic update.", report)

    assert decision.llm_used is True
    assert decision.provider == "Bedrock"
    assert decision.model == "test-model"
    assert decision.bedrock_attempted is True
    assert decision.bedrock_succeeded is True
    assert decision.original_character_count == len("Traffic update.")

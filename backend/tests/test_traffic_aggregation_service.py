"""Tests for deterministic traffic aggregation, provenance, and route ranking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.traffic_report import AlternateRoute
from app.models.traffic_request import TrafficRequest
from app.models.traffic_source import TrafficSource
from app.services.traffic_aggregation_service import (
    TrafficAggregation,
    TrafficAggregationService,
)
from app.services.traffic_intelligence_service import TrafficIntelligenceService
from app.sms.formatter import format_traffic_report


RICH_REPLY = """Corona -> Anaheim
Travel Time: 42 min
Normal Time: 30 min
Traffic Delay: 12 min
• Collision reported
  I-15 N
"""


def test_aggregation_wraps_the_existing_engine_with_primary_provenance() -> None:
    """The current engine is represented as a source without adding a provider."""

    generated_at = datetime(2026, 8, 23, tzinfo=UTC)
    aggregation = TrafficAggregationService().aggregate(
        TrafficRequest(mode="route", origin="CORONA", destination="ANAHEIM"),
        RICH_REPLY,
        generated_at=generated_at,
        generation_duration=timedelta(milliseconds=125),
    )

    assert aggregation.engine_reply == RICH_REPLY
    assert aggregation.sources == (
        TrafficSource(
            source_name="Traffic Engine",
            retrieved_at=generated_at,
            confidence=1.0,
            data_age=timedelta(),
            coverage="route",
            latency=timedelta(milliseconds=125),
            status="AVAILABLE",
        ),
    )


def test_alternate_route_ranking_is_stable_and_deterministic() -> None:
    """Time wins first, followed by savings, confidence, stability, and distance."""

    routes = (
        AlternateRoute("I-5", 30, 7, confidence=0.70, stability=0.90, distance_miles=24),
        AlternateRoute("SR-60", 30, 7, confidence=0.90, stability=0.60, distance_miles=30),
        AlternateRoute("I-15", 30, 5, confidence=1.0, stability=1.0, distance_miles=20),
        AlternateRoute("CA-91", 34, 12, confidence=1.0, stability=1.0, distance_miles=18),
    )

    ranked = TrafficAggregationService.rank_alternate_routes(routes)

    assert [route.name for route in ranked] == ["SR-60", "I-5", "I-15", "CA-91"]


def test_aggregation_provenance_becomes_report_quality_and_sms_freshness() -> None:
    """Report provenance stays structured and can produce a concise freshness note."""

    generated_at = datetime(2026, 8, 23, tzinfo=UTC)
    source = TrafficSource(
        source_name="State DOT",
        retrieved_at=generated_at - timedelta(minutes=2),
        confidence=0.80,
        data_age=timedelta(minutes=2),
        coverage="southern-california",
        latency=timedelta(milliseconds=80),
        status="AVAILABLE",
    )
    aggregation = TrafficAggregation(
        request=TrafficRequest(mode="route", origin="CORONA", destination="ANAHEIM"),
        engine_reply=RICH_REPLY,
        sources=(source,),
        generated_at=generated_at,
        generation_duration=timedelta(milliseconds=80),
    )

    report = TrafficIntelligenceService().build_report(aggregation.request, aggregation)

    assert report.sources == (source,)
    assert report.report_age == timedelta(minutes=2)
    assert report.overall_confidence == 0.9
    assert report.data_quality == "HIGH"
    assert report.generation_duration == timedelta(milliseconds=80)
    assert report.incidents[0].source == "State DOT"
    assert report.incidents[0].severity == "HIGH"
    assert format_traffic_report(report).endswith("Updated 2 min ago.")

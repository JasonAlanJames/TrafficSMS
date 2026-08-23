"""Tests for the sanitized Bedrock traffic-summary contract."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.traffic_incident import TrafficIncident
from app.models.traffic_report import AlternateRoute, TrafficReport
from app.models.traffic_source import TrafficSource
from app.models.traffic_summary_request import TrafficSummaryRequest


def test_summary_request_copies_only_approved_report_facts() -> None:
    """The provider payload contains traffic facts, never services or application state."""

    report = TrafficReport(
        location="Corona -> Anaheim",
        travel_time=42,
        normal_travel_time=30,
        delay_minutes=12,
        congestion_level="HIGH",
        severity="HIGH",
        incidents=(
            TrafficIncident(
                incident_type="Accident",
                severity="HIGH",
                location="I-15 N",
                description="Collision reported.",
                source="State DOT",
                confidence=0.9,
            ),
        ),
        alternate_routes=(AlternateRoute("SR-60", 33, 9),),
        confidence=0.8,
        overall_confidence=0.9,
        sources=(
            TrafficSource(
                source_name="State DOT",
                retrieved_at=datetime(2026, 8, 23, tzinfo=UTC),
                confidence=0.9,
                data_age=timedelta(minutes=2),
                coverage="California",
                latency=timedelta(milliseconds=50),
                status="AVAILABLE",
            ),
        ),
        report_age=timedelta(minutes=2),
        generated_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    request = TrafficSummaryRequest.from_report(report)
    payload = request.as_prompt_payload()

    assert request.confidence == 0.9
    assert request.incidents[0].location == "I-15 N"
    assert request.alternate_routes[0].name == "SR-60"
    assert payload == {
        "location": "Corona -> Anaheim",
        "travel_time": 42,
        "normal_travel_time": 30,
        "delay_minutes": 12,
        "congestion_level": "HIGH",
        "severity": "HIGH",
        "incidents": [
            {
                "incident_type": "Accident",
                "severity": "HIGH",
                "location": "I-15 N",
                "description": "Collision reported.",
                "lanes_affected": None,
            }
        ],
        "alternate_routes": [
            {"name": "SR-60", "travel_time": 33, "savings_minutes": 9}
        ],
        "confidence": 0.9,
        "provenance": [
            {
                "source_name": "State DOT",
                "confidence": 0.9,
                "data_age_seconds": 120,
                "coverage": "California",
                "status": "AVAILABLE",
            }
        ],
        "report_age_seconds": 120,
        "generated_timestamp": "2026-08-23T00:00:00+00:00",
    }

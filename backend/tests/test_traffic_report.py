"""Tests for the immutable canonical traffic response model."""

from __future__ import annotations

from datetime import UTC, datetime

from app.models.traffic_report import AlternateRoute, TrafficIncidentSummary, TrafficReport


def test_traffic_report_preserves_structured_response_fields() -> None:
    """The report is the complete, provider-neutral traffic response contract."""

    generated_at = datetime(2026, 8, 23, tzinfo=UTC)
    incident = TrafficIncidentSummary("Accident", "Collision reported", "I-15 N")
    alternate = AlternateRoute("SR-60", travel_time=33, savings_minutes=9)

    report = TrafficReport(
        location="Corona -> Anaheim",
        travel_time=42,
        normal_travel_time=30,
        delay_minutes=12,
        congestion_level="HIGH",
        severity="HIGH",
        incidents=(incident,),
        alternate_routes=(alternate,),
        confidence=1.0,
        generated_at=generated_at,
    )

    assert report.location == "Corona -> Anaheim"
    assert report.incidents[0].category == "Accident"
    assert report.alternate_routes[0].savings_minutes == 9
    assert report.generated_at is generated_at

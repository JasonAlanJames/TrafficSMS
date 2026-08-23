"""Tests for source and incident provenance models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.traffic_incident import TrafficIncident
from app.models.traffic_source import TrafficSource


def test_traffic_source_records_retrieval_quality_and_operational_metadata() -> None:
    """Each source has the fields required for future provider attribution."""

    retrieved_at = datetime(2026, 8, 23, tzinfo=UTC)
    source = TrafficSource(
        source_name="State DOT",
        retrieved_at=retrieved_at,
        confidence=0.92,
        data_age=timedelta(minutes=1),
        coverage="California",
        latency=timedelta(milliseconds=140),
        status="AVAILABLE",
    )

    assert source.source_name == "State DOT"
    assert source.data_age == timedelta(minutes=1)
    assert source.latency == timedelta(milliseconds=140)


def test_traffic_incident_preserves_normalized_details_and_compatibility_aliases() -> None:
    """New incident details coexist with Revision 3.2 formatter properties."""

    started_at = datetime(2026, 8, 23, tzinfo=UTC)
    incident = TrafficIncident(
        incident_type="Lane Closure",
        severity="HIGH",
        location="I-15 N",
        description="Two lanes closed after a collision.",
        lanes_affected=2,
        started_at=started_at,
        estimated_clearance=started_at + timedelta(minutes=30),
        source="State DOT",
        confidence=0.88,
    )

    assert incident.category == "Lane Closure"
    assert incident.road_name == "I-15 N"
    assert incident.lanes_affected == 2
    assert incident.source == "State DOT"

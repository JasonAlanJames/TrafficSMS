"""Tests for deterministic traffic enrichment and SMS presentation."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy.orm import Session

from app.models.entities import User
from app.models.traffic_report import AlternateRoute
from app.models.traffic_request import TrafficRequest
from app.services.traffic_intelligence_service import TrafficIntelligenceService
from app.services.traffic_service import TrafficService
from app.sms.context import SMSContext
from app.sms.formatter import format_traffic_report


RICH_ROUTE_REPLY = """TrafficSMS

Corona -> Anaheim

Travel Time: 42 min
Normal Time: 30 min
Traffic Delay: 12 min

Alternate: SR-60 - 33 min (saves 9 min)
• Collision reported
  I-15 N
• Roadwork
  SR-91 W
• Lane closure
  I-5 S
• Rain advisory
  Orange County
"""


def test_intelligence_service_builds_complete_route_report() -> None:
    """Legacy route output is normalized into the canonical report model."""

    report = TrafficIntelligenceService().build_report(
        TrafficRequest(mode="route", origin="CORONA", destination="ANAHEIM"),
        RICH_ROUTE_REPLY,
        generated_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    assert report.location == "Corona -> Anaheim"
    assert report.travel_time == 42
    assert report.normal_travel_time == 30
    assert report.delay_minutes == 12
    assert report.congestion_level == "HIGH"
    assert report.severity == "HIGH"
    assert [incident.category for incident in report.incidents] == [
        "Accident",
        "Construction",
        "Lane Closure",
        "Weather",
    ]
    assert report.construction[0].road_name == "SR-91 W"
    assert report.lane_closures[0].road_name == "I-5 S"
    assert report.weather_impacts == ("Rain advisory",)
    assert report.alternate_routes == (AlternateRoute("SR-60", 33, 9),)
    assert report.confidence == 1.0


@pytest.mark.parametrize(
    ("delay_minutes", "congestion_level", "expected"),
    [
        (5, "LOW", "LOW"),
        (6, "LOW", "MODERATE"),
        (16, "MODERATE", "HIGH"),
        (31, "HIGH", "SEVERE"),
        (2, "SEVERE", "SEVERE"),
    ],
)
def test_severity_uses_the_highest_delay_or_congestion_band(
    delay_minutes: int,
    congestion_level: str,
    expected: str,
) -> None:
    """Severity is deterministic and protects against under-reporting congestion."""

    assert (
        TrafficIntelligenceService.classify_severity(
            delay_minutes=delay_minutes,
            congestion_level=congestion_level,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Accident on I-5", "Accident"),
        ("Disabled vehicle on SR-91", "Disabled Vehicle"),
        ("Debris road hazard", "Road Hazard"),
        ("Lane closure ahead", "Lane Closure"),
        ("Construction on I-15", "Construction"),
        ("CHP activity", "Police Activity"),
        ("Fog weather advisory", "Weather"),
        ("Brush fire nearby", "Fire"),
    ],
)
def test_incident_categories_are_normalized(description: str, expected: str) -> None:
    """Provider wording maps to the stable public incident vocabulary."""

    report = TrafficIntelligenceService().build_report(
        TrafficRequest(mode="area", area="CORONA"),
        description,
    )

    assert report.incidents[0].category == expected


def test_alternate_routes_accept_structured_data_and_calculate_savings() -> None:
    """A provider can add alternate routes without formatter or engine changes."""

    report = TrafficIntelligenceService().build_report(
        TrafficRequest(mode="route", origin="CORONA", destination="ANAHEIM"),
        "Travel Time: 42 min\nNormal Time: 30 min\nTraffic Delay: 12 min",
        alternate_routes=(
            {"route_name": "SR-60", "travel_time": 33},
            {"name": "I-5", "travel_time": 38, "savings_minutes": 4},
        ),
    )

    assert report.alternate_routes[0] == AlternateRoute("SR-60", 33, 9)
    assert report.alternate_routes[1] == AlternateRoute("I-5", 38, 4)


def test_formatter_emits_a_concise_rich_sms() -> None:
    """The formatter presents only the decision-useful traffic facts."""

    report = TrafficIntelligenceService().build_report(
        TrafficRequest(mode="route", origin="CORONA", destination="ANAHEIM"),
        RICH_ROUTE_REPLY,
    )

    assert format_traffic_report(report) == (
        "TrafficSMS\n"
        "Corona -> Anaheim\n"
        "Travel: 42 min (+12 min delay)\n"
        "Traffic: High congestion\n"
        "Incident: Accident on I-15 N\n"
        "Alt: SR-60, 33 min (saves 9 min)"
    )


def test_formatter_preserves_a_legacy_summary_without_structured_data() -> None:
    """Area and corridor engines retain their current response until enriched data exists."""

    raw_reply = "Corona traffic is moving normally."
    report = TrafficIntelligenceService().build_report(
        TrafficRequest(mode="area", area="CORONA"), raw_reply
    )

    assert format_traffic_report(report) == raw_reply
    assert report.confidence == 0.2


def test_traffic_service_enriches_but_only_invokes_the_existing_engine(
    monkeypatch,
) -> None:
    """TrafficService remains the sole bridge to the unchanged traffic engine."""

    user = User(id=1, email="driver@example.com", phone_e164="+17145550123")
    context = SMSContext(
        db=cast(Session, object()),
        phone_number=user.phone_e164,
        user=user,
        subscription=None,
        normalized_text="TRAFFIC CORONA TO ANAHEIM",
        raw_text="traffic corona to anaheim",
        tokens=("TRAFFIC", "CORONA", "TO", "ANAHEIM"),
        parsed_arguments=("CORONA", "TO", "ANAHEIM"),
        timestamp=datetime.now(UTC),
    )
    request = TrafficRequest(mode="route", origin="CORONA", destination="ANAHEIM")

    async def fake_build_traffic_reply(**kwargs: object) -> str:
        assert kwargs["request"] is request
        return RICH_ROUTE_REPLY

    monkeypatch.setattr(
        "app.services.traffic_service.build_traffic_reply", fake_build_traffic_reply
    )

    result = asyncio.run(TrafficService().build_reply(context, request))

    assert result.report is not None
    assert result.report.severity == "HIGH"
    assert "Travel: 42 min" in result.message
    assert result.metadata == {"traffic_mode": "route"}

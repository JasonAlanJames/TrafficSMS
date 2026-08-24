"""Traffic report and direct internal coverage reply tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.models.entities import CommunityReport
from app.models.traffic_request import TrafficRequest
from app.services.incident_coverage_service import IncidentCoverageService
from app.services.traffic_aggregation_service import TrafficAggregationService
from app.services.traffic_area import build_area_reply
from app.services.traffic_corridor import build_corridor_reply
from app.services.traffic_intelligence_service import TrafficIntelligenceService
from app.sms.formatter import format_traffic_report


def _active_report(report_type: str, road_name: str, area: str) -> CommunityReport:
    now = datetime.now(UTC).replace(tzinfo=None)
    return CommunityReport(
        report_type=report_type,
        road_name=road_name,
        area_label=area,
        expires_at=now + timedelta(hours=1),
        reported_at=now,
    )


def test_coverage_populates_report_and_sms_sections(db_session) -> None:
    db_session.add_all([
        _active_report("lane_closure", "SR-91", "Corona"),
        _active_report("construction", "I-15", "Corona"),
        _active_report("flooding", "Main Street", "Corona"),
    ])
    db_session.commit()
    request = TrafficRequest(mode="area", area="Corona")
    coverage = asyncio.run(IncidentCoverageService().collect(db_session, request))
    aggregation = TrafficAggregationService().aggregate(request, "", coverage=coverage)
    report = TrafficIntelligenceService().build_report(request, aggregation)
    message = format_traffic_report(report)

    assert report.lane_closures
    assert report.construction
    assert report.weather_impacts
    assert "Lane closure: SR-91" in message
    assert "Construction: I-15" in message


def test_area_and_corridor_replies_use_internal_coverage_and_safe_fallback(db_session, monkeypatch) -> None:
    db_session.add(_active_report("accident", "SR-91", "Corona"))
    db_session.commit()

    async def resolve_location(**_kwargs):
        return SimpleNamespace(formatted_address="Corona")

    monkeypatch.setattr("app.services.traffic_area.location_resolver.resolve_location", resolve_location)
    area_reply = asyncio.run(build_area_reply(db_session, TrafficRequest(mode="area", area="Corona")))
    corridor_reply = asyncio.run(build_corridor_reply(
        db_session, TrafficRequest(mode="corridor", corridor="SR-91", direction="WEST"),
    ))
    fallback = asyncio.run(build_corridor_reply(
        db_session, TrafficRequest(mode="corridor", corridor="I-15", direction="NORTH"),
    ))

    assert "Accident" in area_reply
    assert "Accident" in corridor_reply
    assert "No active community incidents or closures found" in fallback

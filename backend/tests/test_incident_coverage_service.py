"""Active internal coverage normalization tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.models.entities import CommunityReport, DuiNotice, EnforcementCamera
from app.models.traffic_incident import TrafficIncident
from app.models.traffic_provider_result import TrafficClosure, TrafficProviderResult, TrafficWeather
from app.models.traffic_request import TrafficRequest
from app.services.incident_coverage_service import IncidentCoverageService


def test_coverage_collects_only_active_internal_records(db_session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add_all([
        CommunityReport(report_type="accident", road_name="SR-91", direction="WEST", area_label="Corona", expires_at=now + timedelta(hours=1), reported_at=now, still_there_votes=2),
        CommunityReport(report_type="closure", road_name="I-15", direction="NORTH", area_label="Corona", expires_at=now - timedelta(minutes=1), reported_at=now),
        EnforcementCamera(camera_type="speed_camera", road_name="SR-91", area_label="Corona", direction="WEST", latitude=33.8, longitude=-117.5, source_type="internal", active=True, verified=True),
        EnforcementCamera(camera_type="speed_camera", road_name="I-15", area_label="Riverside", direction="NORTH", latitude=33.9, longitude=-117.4, source_type="internal", active=False),
        DuiNotice(agency="CHP", area_label="Corona", notice_text="Safety checkpoint notice", source_url="https://traffic.local/notice", starts_at=now - timedelta(hours=1), ends_at=now + timedelta(hours=1), published_at=now),
        DuiNotice(agency="CHP", area_label="Corona", notice_text="Expired notice", source_url="https://traffic.local/expired", starts_at=now - timedelta(days=1), ends_at=now - timedelta(hours=1), published_at=now),
    ])
    db_session.commit()

    coverage = asyncio.run(IncidentCoverageService().collect(
        db_session, TrafficRequest(mode="area", area="Corona"),
    ))

    assert {item.category for item in coverage} == {"accident", "camera", "dui_notice"}
    assert {item.source for item in coverage} == {"community", "enforcement_camera_verified", "official_dui_notice"}
    assert all(item.is_active for item in coverage)
    assert all("reporter" not in item.description.lower() for item in coverage)


def test_coverage_normalizes_provider_result_without_external_calls(db_session) -> None:
    provider_result = TrafficProviderResult(
        provider="test_provider",
        provider_type="test",
        confidence=0.8,
        incidents=(TrafficIncident("Road Hazard", "MODERATE", "SR-91", "Debris reported."),),
        closures=(TrafficClosure("SR-91", "Westbound lanes closed."),),
        construction=(TrafficClosure("I-15", "Night construction."),),
        weather=(TrafficWeather("Corona", "Heavy rain", "MODERATE"),),
    )

    coverage = asyncio.run(IncidentCoverageService().collect(
        db_session,
        TrafficRequest(mode="corridor", corridor="SR-91", direction="WEST"),
        provider_result=provider_result,
    ))

    assert {item.category for item in coverage} == {"hazard", "closure", "construction", "weather"}
    assert {item.source for item in coverage} == {"test_provider"}

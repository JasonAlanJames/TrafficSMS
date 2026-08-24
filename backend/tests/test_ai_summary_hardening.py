"""Revision 5.8 deterministic-first AI summary guardrail coverage."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

from app.llm.summary_formatter import SummaryFormatter
from app.llm.traffic_summary_service import TrafficSummaryService
from app.models.incident_coverage import IncidentCoverageItem
from app.models.traffic_incident import TrafficIncident
from app.models.traffic_report import TrafficReport
from app.models.traffic_summary_request import TrafficSummaryRequest


def _report() -> TrafficReport:
    return TrafficReport(
        location="Corona to Anaheim",
        travel_time=42,
        normal_travel_time=30,
        delay_minutes=12,
        congestion_level="HIGH",
        severity="HIGH",
        incidents=(TrafficIncident("Accident", "HIGH", "SR-91", "Collision on SR-91."),),
        coverage=(
            IncidentCoverageItem("closure", "Road closure", "Westbound lanes closed.", "Corona", "SR-91", severity="HIGH", source="community"),
            IncidentCoverageItem("camera", "Speed camera", "Speed camera near SR-91.", "Corona", "SR-91", source="enforcement_camera"),
            IncidentCoverageItem("dui_notice", "Official DUI notice", "Official DUI notice in Corona.", "Corona", severity="MODERATE", source="official_dui_notice"),
        ),
        generated_at=datetime(2026, 8, 24, tzinfo=UTC),
    )


def test_summary_request_carries_bounded_coverage_without_user_data() -> None:
    report = _report()
    report = replace(report, incidents=report.incidents * 6)
    request = TrafficSummaryRequest.from_report(report, max_input_incidents=2)
    payload = request.as_prompt_payload()

    assert len(request.incidents) == 2
    assert [item.category for item in request.coverage] == ["closure", "camera"]
    assert "email" not in str(payload).lower()
    assert "phone" not in str(payload).lower()
    assert "user_id" not in str(payload).lower()


def test_summary_formatter_rejects_unsafe_or_ungrounded_coverage_claims() -> None:
    request = TrafficSummaryRequest.from_report(_report())
    formatter = SummaryFormatter(max_output_chars=320)
    grounded = "Corona to Anaheim has HIGH traffic: 42 min with 12 min delay. Accident, road closure, camera, and official DUI notice on SR-91."

    assert formatter.format(grounded, request) == grounded
    assert formatter.format("Corona to Anaheim has HIGH traffic: 42 min with 12 min delay. Avoid the DUI checkpoint on SR-91.", request) is None
    assert formatter.format("Corona to Anaheim has HIGH traffic: 42 min with 12 min delay. Road closure on I-405.", request) is None
    assert formatter.format("Corona to Anaheim has HIGH traffic: 42 min with 12 min delay. Police activity on SR-91.", request) is None
    assert formatter.format("- Corona to Anaheim has HIGH traffic: 42 min with 12 min delay.", request) is None
    assert formatter.format("Corona to Anaheim has HIGH traffic: 42 min with 12 min delay. " + "x" * 300, request) is None


def test_summary_service_is_disabled_by_default_and_records_safe_fallback() -> None:
    class NeverCalledProvider:
        async def summarize(self, _request):
            raise AssertionError("disabled summaries must not call the provider")

    service = TrafficSummaryService(
        settings=SimpleNamespace(bedrock_enabled=False), provider=NeverCalledProvider(),
    )
    result = asyncio.run(service.summarize(_report(), "Deterministic reply."))

    assert result == "Deterministic reply."
    assert service.metadata.summary_attempted is False
    assert service.metadata.summary_used is False


def test_summary_service_uses_grounded_output_and_rejects_bad_provider_output() -> None:
    class GroundedProvider:
        async def summarize(self, _request):
            return "Corona to Anaheim has HIGH traffic: 42 min with 12 min delay. Accident, road closure, camera, and official DUI notice on SR-91."

    settings = SimpleNamespace(bedrock_enabled=True, bedrock_model_id="test-model", ai_summary_max_input_incidents=5, ai_summary_max_output_chars=320)
    service = TrafficSummaryService(settings=settings, provider=GroundedProvider())
    accepted = asyncio.run(service.summarize(_report(), "Deterministic reply."))
    assert accepted.startswith("Corona to Anaheim")
    assert service.metadata.summary_attempted is True
    assert service.metadata.summary_used is True

    class UnsafeProvider:
        async def summarize(self, _request):
            return "Corona to Anaheim has HIGH traffic: 42 min with 12 min delay. Avoid the DUI checkpoint."

    service = TrafficSummaryService(settings=settings, provider=UnsafeProvider())
    assert asyncio.run(service.summarize(_report(), "Deterministic reply.")) == "Deterministic reply."
    assert service.metadata.fallback_used is True
    assert service.metadata.grounding_verified is False

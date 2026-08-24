"""Collect active, source-attributed incident coverage from existing sources."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.incident_coverage import IncidentCoverageItem
from app.models.traffic_provider_result import TrafficProviderResult
from app.models.traffic_request import TrafficRequest
from app.services.providers.community_provider import community_provider


_COMMUNITY_CATEGORY_MAP = {
    "police_visible": "police", "police_hidden": "police", "police_opposite_side": "police",
    "crash": "accident", "accident": "accident", "collision": "accident",
    "disabled_vehicle": "disabled_vehicle", "stalled_vehicle": "disabled_vehicle",
    "road_hazard": "hazard", "debris": "hazard", "hazard": "hazard",
    "flooding": "weather", "weather": "weather",
    "closure": "closure", "road_closure": "closure",
    "lane_closure": "lane_closure", "construction": "construction",
    "camera": "camera", "speed_camera": "camera",
    "dui": "dui_notice", "dui_checkpoint": "dui_notice",
}
_SEVERITY = {
    "accident": "HIGH", "closure": "HIGH", "lane_closure": "HIGH",
    "hazard": "MODERATE", "disabled_vehicle": "MODERATE", "weather": "MODERATE",
    "construction": "MODERATE", "police": "MODERATE", "camera": "LOW", "dui_notice": "MODERATE",
}


class IncidentCoverageService:
    """Normalize internal coverage without external calls or SMS formatting."""

    async def collect(
        self,
        db: Session,
        request: TrafficRequest,
        *,
        provider_result: TrafficProviderResult | None = None,
        location_hints: Iterable[str] = (),
    ) -> tuple[IncidentCoverageItem, ...]:
        """Return only active facts relevant to the requested area, route, or corridor."""

        if not hasattr(db, "scalars"):
            return self._deduplicate(self._from_provider_result(provider_result)) if provider_result else ()
        terms = self._terms(request, location_hints)
        reports = await community_provider.get_active_reports(db=db, terms=terms)
        cameras = await community_provider.get_active_cameras(db=db, terms=terms)
        notices = await community_provider.get_active_dui_notices(db=db, terms=terms)
        items = [
            *(self._from_report(report) for report in reports),
            *(self._from_camera(camera) for camera in cameras),
            *(self._from_dui_notice(notice) for notice in notices),
        ]
        if provider_result is not None:
            items.extend(self._from_provider_result(provider_result))
        return self._deduplicate(items)

    @staticmethod
    def _terms(request: TrafficRequest, location_hints: Iterable[str]) -> tuple[str, ...]:
        values = [*location_hints]
        if request.mode in {"route", "commute"}:
            values.extend((request.origin or "", request.destination or ""))
        elif request.mode == "corridor":
            values.extend((request.corridor or "", request.direction or ""))
        else:
            values.append(request.area or "")
        return tuple(value.strip() for value in values if value and value.strip())

    @staticmethod
    def _from_report(report) -> IncidentCoverageItem:
        report_type = (report.report_type or "general").lower()
        category = _COMMUNITY_CATEGORY_MAP.get(report_type, "general")
        confirmations = max((report.still_there_votes or 0) - (report.cleared_votes or 0), 0)
        confidence = min(0.55 + confirmations * 0.1, 0.95)
        location = report.area_label or report.road_name
        return IncidentCoverageItem(
            category=category,
            title=report_type.replace("_", " ").title(),
            description=f"{report_type.replace('_', ' ').title()} reported near {report.road_name}.",
            location_text=location,
            road_name=report.road_name,
            direction=report.direction,
            severity=_SEVERITY.get(category, "LOW"),
            confidence=confidence,
            source="community",
            started_at=report.reported_at,
            expires_at=report.expires_at,
            metadata=(("confirmation_count", str(confirmations)),),
        )

    @staticmethod
    def _from_camera(camera) -> IncidentCoverageItem:
        source = "enforcement_camera_verified" if camera.verified else "enforcement_camera"
        return IncidentCoverageItem(
            category="camera",
            title=camera.camera_type.replace("_", " ").title(),
            description=f"{camera.camera_type.replace('_', ' ').title()} near {camera.road_name}.",
            location_text=camera.area_label,
            road_name=camera.road_name,
            direction=camera.direction,
            severity="LOW",
            confidence=0.9 if camera.verified else 0.6,
            source=source,
        )

    @staticmethod
    def _from_dui_notice(notice) -> IncidentCoverageItem:
        return IncidentCoverageItem(
            category="dui_notice",
            title="Official DUI notice",
            description=f"Official DUI notice from {notice.agency} in {notice.area_label}.",
            location_text=notice.area_label,
            severity="MODERATE",
            confidence=0.95,
            source="official_dui_notice",
            started_at=notice.starts_at,
            expires_at=notice.ends_at,
        )

    @staticmethod
    def _from_provider_result(result: TrafficProviderResult) -> list[IncidentCoverageItem]:
        items: list[IncidentCoverageItem] = []
        for incident in result.incidents:
            category = IncidentCoverageService._incident_category(incident.incident_type)
            items.append(IncidentCoverageItem(
                category=category,
                title=incident.incident_type,
                description=incident.description,
                location_text=incident.location,
                road_name=incident.road_name,
                severity=incident.severity,
                confidence=incident.confidence or result.confidence,
                source=result.provider,
                started_at=incident.started_at,
                expires_at=incident.estimated_clearance,
            ))
        for closure in result.closures:
            items.append(IncidentCoverageItem("closure", "Road closure", closure.description, closure.location, closure.location, severity="HIGH", confidence=result.confidence, source=result.provider))
        for construction in result.construction:
            items.append(IncidentCoverageItem("construction", "Construction", construction.description, construction.location, construction.location, severity="MODERATE", confidence=result.confidence, source=result.provider))
        for weather in result.weather:
            items.append(IncidentCoverageItem("weather", "Weather impact", weather.description, weather.location, weather.location, severity=weather.severity, confidence=result.confidence, source=result.provider))
        return items

    @staticmethod
    def _incident_category(incident_type: str) -> str:
        return {
            "Accident": "accident", "Disabled Vehicle": "disabled_vehicle",
            "Road Hazard": "hazard", "Lane Closure": "lane_closure",
            "Construction": "construction", "Police Activity": "police", "Weather": "weather",
        }.get(incident_type, "general")

    @staticmethod
    def _deduplicate(items: Iterable[IncidentCoverageItem]) -> tuple[IncidentCoverageItem, ...]:
        priority = {"SEVERE": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
        unique: dict[tuple[str, str, str], IncidentCoverageItem] = {}
        for item in items:
            unique.setdefault((item.category, item.road_name or "", item.description), item)
        return tuple(sorted(unique.values(), key=lambda item: (priority.get(item.severity, 4), -item.confidence, item.title)))


incident_coverage_service = IncidentCoverageService()

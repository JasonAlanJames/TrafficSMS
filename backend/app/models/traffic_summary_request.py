"""The intentionally limited traffic payload visible to a summary provider."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.traffic_report import TrafficReport


@dataclass(frozen=True, slots=True)
class TrafficSummaryIncident:
    """Incident facts safe to send to a natural-language summary provider."""

    incident_type: str
    severity: str
    location: str
    description: str
    lanes_affected: int | None = None


@dataclass(frozen=True, slots=True)
class TrafficSummaryAlternateRoute:
    """Alternate-route facts safe to send to a summary provider."""

    name: str
    travel_time: int | None
    savings_minutes: int | None


@dataclass(frozen=True, slots=True)
class TrafficSummarySource:
    """Minimal provenance suitable for a natural-language summary."""

    source_name: str
    confidence: float
    data_age_seconds: int
    coverage: str
    status: str


@dataclass(frozen=True, slots=True)
class TrafficSummaryCoverage:
    """Safe, bounded Revision 5.7 coverage facts for optional AI wording."""

    category: str
    title: str
    description: str
    location: str
    road_name: str | None
    severity: str
    confidence: float
    source: str


@dataclass(frozen=True, slots=True)
class TrafficSummaryRequest:
    """The complete and exclusive data contract for Bedrock summarization."""

    location: str
    travel_time: int | None
    normal_travel_time: int | None
    delay_minutes: int | None
    congestion_level: str
    severity: str
    incidents: tuple[TrafficSummaryIncident, ...]
    alternate_routes: tuple[TrafficSummaryAlternateRoute, ...]
    confidence: float
    provenance: tuple[TrafficSummarySource, ...]
    report_age: timedelta | None
    generated_timestamp: datetime
    closures: tuple[TrafficSummaryIncident, ...] = ()
    lane_closures: tuple[TrafficSummaryIncident, ...] = ()
    construction: tuple[TrafficSummaryIncident, ...] = ()
    weather_impacts: tuple[str, ...] = ()
    coverage: tuple[TrafficSummaryCoverage, ...] = ()

    @classmethod
    def from_report(
        cls,
        report: "TrafficReport",
        *,
        max_input_incidents: int = 5,
    ) -> "TrafficSummaryRequest":
        """Copy only approved report facts into the provider-facing request."""

        return cls(
            location=report.location,
            travel_time=report.travel_time,
            normal_travel_time=report.normal_travel_time,
            delay_minutes=report.delay_minutes,
            congestion_level=report.congestion_level,
            severity=report.severity,
            incidents=tuple(
                TrafficSummaryIncident(
                    incident_type=incident.category,
                    severity=getattr(incident, "severity", report.severity),
                    location=incident.road_name or "",
                    description=incident.description,
                    lanes_affected=getattr(incident, "lanes_affected", None),
                )
                for incident in report.incidents[:max_input_incidents]
            ),
            closures=cls._summary_incidents(report.closures, max_input_incidents),
            lane_closures=cls._summary_incidents(report.lane_closures, max_input_incidents),
            construction=cls._summary_incidents(report.construction, max_input_incidents),
            weather_impacts=tuple(report.weather_impacts[:max_input_incidents]),
            coverage=tuple(
                TrafficSummaryCoverage(
                    category=item.category,
                    title=item.title,
                    description=item.description,
                    location=item.location_text,
                    road_name=item.road_name,
                    severity=item.severity,
                    confidence=item.confidence,
                    source=item.source,
                )
                for item in report.coverage[:max_input_incidents]
            ),
            alternate_routes=tuple(
                TrafficSummaryAlternateRoute(
                    name=route.name,
                    travel_time=route.travel_time,
                    savings_minutes=route.savings_minutes,
                )
                for route in report.alternate_routes
            ),
            confidence=report.overall_confidence or report.confidence,
            provenance=tuple(
                TrafficSummarySource(
                    source_name=source.source_name,
                    confidence=source.confidence,
                    data_age_seconds=max(int(source.data_age.total_seconds()), 0),
                    coverage=source.coverage,
                    status=source.status,
                )
                for source in report.sources
            ),
            report_age=report.report_age,
            generated_timestamp=report.generated_at,
        )

    @staticmethod
    def _summary_incidents(
        incidents: tuple[object, ...],
        max_input_incidents: int,
    ) -> tuple[TrafficSummaryIncident, ...]:
        return tuple(
            TrafficSummaryIncident(
                incident_type=incident.category,
                severity=getattr(incident, "severity", "LOW"),
                location=incident.road_name or "",
                description=incident.description,
                lanes_affected=getattr(incident, "lanes_affected", None),
            )
            for incident in incidents[:max_input_incidents]
        )

    def as_prompt_payload(self) -> dict[str, object]:
        """Return JSON-compatible facts with no application objects or secrets."""

        return {
            "location": self.location,
            "travel_time": self.travel_time,
            "normal_travel_time": self.normal_travel_time,
            "delay_minutes": self.delay_minutes,
            "congestion_level": self.congestion_level,
            "severity": self.severity,
            "incidents": [asdict(incident) for incident in self.incidents],
            "closures": [asdict(incident) for incident in self.closures],
            "lane_closures": [asdict(incident) for incident in self.lane_closures],
            "construction": [asdict(incident) for incident in self.construction],
            "weather_impacts": list(self.weather_impacts),
            "coverage": [asdict(item) for item in self.coverage],
            "alternate_routes": [asdict(route) for route in self.alternate_routes],
            "confidence": self.confidence,
            "provenance": [asdict(source) for source in self.provenance],
            "report_age_seconds": (
                max(int(self.report_age.total_seconds()), 0)
                if self.report_age is not None
                else None
            ),
            "generated_timestamp": self.generated_timestamp.isoformat(),
        }

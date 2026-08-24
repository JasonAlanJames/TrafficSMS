"""Structured, provider-neutral traffic response data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal

from app.models.traffic_incident import IncidentType, TrafficIncident
from app.models.traffic_source import TrafficSource
from app.models.traffic_freshness import TrafficFreshness
from app.models.summary_metadata import SummaryMetadata
from app.models.incident_coverage import IncidentCoverageItem

Severity = Literal["LOW", "MODERATE", "HIGH", "SEVERE"]
CongestionLevel = Literal["UNKNOWN", "LOW", "MODERATE", "HIGH", "SEVERE"]
IncidentCategory = IncidentType
DataQuality = Literal["UNKNOWN", "LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True, slots=True)
class TrafficIncidentSummary:
    """A normalized incident suitable for transport-independent presentation."""

    category: IncidentCategory
    description: str
    road_name: str | None = None
    delay_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class AlternateRoute:
    """A comparable alternate route, including any calculated time savings."""

    name: str
    travel_time: int | None = None
    savings_minutes: int | None = None
    confidence: float = 0.5
    stability: float = 0.5
    distance_miles: float | None = None


@dataclass(frozen=True, slots=True)
class TrafficReport:
    """Canonical enriched traffic response consumed by the SMS formatter."""

    location: str
    travel_time: int | None = None
    normal_travel_time: int | None = None
    delay_minutes: int | None = None
    congestion_level: CongestionLevel = "UNKNOWN"
    severity: Severity = "LOW"
    incidents: tuple[TrafficIncident | TrafficIncidentSummary, ...] = ()
    closures: tuple[TrafficIncident | TrafficIncidentSummary, ...] = ()
    construction: tuple[TrafficIncident | TrafficIncidentSummary, ...] = ()
    lane_closures: tuple[TrafficIncident | TrafficIncidentSummary, ...] = ()
    weather_impacts: tuple[str, ...] = ()
    coverage: tuple[IncidentCoverageItem, ...] = ()
    alternate_routes: tuple[AlternateRoute, ...] = ()
    confidence: float = 0.0
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_summary: str | None = None
    sources: tuple[TrafficSource, ...] = ()
    report_age: timedelta | None = None
    overall_confidence: float = 0.0
    data_quality: DataQuality = "UNKNOWN"
    generation_duration: timedelta = field(default_factory=timedelta)
    freshness: TrafficFreshness = field(default_factory=TrafficFreshness)
    processing_duration_ms: int = 0
    summary_metadata: SummaryMetadata = field(default_factory=SummaryMetadata)
    request: str = ""
    route: str = ""

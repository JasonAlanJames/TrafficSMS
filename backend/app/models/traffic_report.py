"""Structured, provider-neutral traffic response data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


Severity = Literal["LOW", "MODERATE", "HIGH", "SEVERE"]
CongestionLevel = Literal["UNKNOWN", "LOW", "MODERATE", "HIGH", "SEVERE"]
IncidentCategory = Literal[
    "Accident",
    "Disabled Vehicle",
    "Road Hazard",
    "Lane Closure",
    "Construction",
    "Police Activity",
    "Weather",
    "Fire",
]


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


@dataclass(frozen=True, slots=True)
class TrafficReport:
    """Canonical enriched traffic response consumed by the SMS formatter."""

    location: str
    travel_time: int | None = None
    normal_travel_time: int | None = None
    delay_minutes: int | None = None
    congestion_level: CongestionLevel = "UNKNOWN"
    severity: Severity = "LOW"
    incidents: tuple[TrafficIncidentSummary, ...] = ()
    construction: tuple[TrafficIncidentSummary, ...] = ()
    lane_closures: tuple[TrafficIncidentSummary, ...] = ()
    weather_impacts: tuple[str, ...] = ()
    alternate_routes: tuple[AlternateRoute, ...] = ()
    confidence: float = 0.0
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_summary: str | None = None

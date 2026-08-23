"""Canonical normalized output contract for all future traffic providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.models.traffic_incident import TrafficIncident
from app.models.traffic_report import AlternateRoute


@dataclass(frozen=True, slots=True)
class TrafficTravelTime:
    location: str
    travel_time_minutes: int | None = None
    normal_travel_time_minutes: int | None = None
    delay_minutes: int | None = None


@dataclass(frozen=True, slots=True)
class TrafficClosure:
    location: str
    description: str
    lanes_affected: int | None = None


@dataclass(frozen=True, slots=True)
class TrafficWeather:
    location: str
    description: str
    severity: str = "LOW"


@dataclass(frozen=True, slots=True)
class ProviderResultMetadata:
    request_id: str = ""
    cache_hit: bool = False
    cache_age: timedelta = timedelta()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TrafficProviderResult:
    """Provider-neutral traffic facts; providers must never return raw mappings."""

    provider: str
    provider_type: str
    incidents: tuple[TrafficIncident, ...] = ()
    travel_times: tuple[TrafficTravelTime, ...] = ()
    closures: tuple[TrafficClosure, ...] = ()
    construction: tuple[TrafficClosure, ...] = ()
    weather: tuple[TrafficWeather, ...] = ()
    alternate_routes: tuple[AlternateRoute, ...] = ()
    confidence: float = 0.0
    latency_ms: int = 0
    freshness: timedelta = timedelta()
    coverage: str = ""
    metadata: ProviderResultMetadata = field(default_factory=ProviderResultMetadata)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

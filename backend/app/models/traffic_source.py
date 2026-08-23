"""Provenance metadata for a traffic data source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal


SourceStatus = Literal["AVAILABLE", "STALE", "UNAVAILABLE"]


@dataclass(frozen=True, slots=True)
class TrafficSource:
    """A normalized source contribution included in a traffic report."""

    source_name: str
    retrieved_at: datetime
    confidence: float
    data_age: timedelta
    coverage: str
    latency: timedelta
    status: SourceStatus
    provider_name: str = ""
    provider_type: str = ""
    provider_version: str = ""
    authoritative: bool = False
    license: str = ""
    attribution: str = ""
    url: str = ""
    last_updated: datetime = datetime.min.replace(tzinfo=UTC)
    latency_ms: int = 0
    response_time_ms: int = 0
    fetch_duration_ms: int = 0
    request_id: str = ""
    cache_hit: bool = False
    cache_age: timedelta = timedelta()
    is_live: bool = False
    is_verified: bool = False
    supports_incidents: bool = False
    supports_routes: bool = False
    supports_predictions: bool = False
    metadata: tuple[tuple[str, str], ...] = ()

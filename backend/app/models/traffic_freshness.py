"""Deterministic freshness metrics derived from report sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True, slots=True)
class TrafficFreshness:
    oldest_source_age: timedelta = timedelta()
    newest_source_age: timedelta = timedelta()
    average_source_age: timedelta = timedelta()
    is_live: bool = False
    generated_at: datetime = datetime.min.replace(tzinfo=UTC)
    processing_duration_ms: int = 0
    refresh_interval: timedelta = timedelta()

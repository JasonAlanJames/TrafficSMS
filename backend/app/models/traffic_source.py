"""Provenance metadata for a traffic data source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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

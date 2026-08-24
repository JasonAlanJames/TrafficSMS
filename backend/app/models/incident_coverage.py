"""Normalized internal incident and closure coverage for traffic reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


CoverageCategory = Literal[
    "accident", "closure", "lane_closure", "construction", "hazard",
    "disabled_vehicle", "weather", "police", "camera", "dui_notice", "general",
]


@dataclass(frozen=True, slots=True)
class IncidentCoverageItem:
    """A source-attributed fact suitable for deterministic traffic presentation."""

    category: CoverageCategory
    title: str
    description: str
    location_text: str
    road_name: str | None = None
    direction: str | None = None
    severity: str = "LOW"
    confidence: float = 0.0
    source: str = "internal"
    status: str = "active"
    started_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool = True
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

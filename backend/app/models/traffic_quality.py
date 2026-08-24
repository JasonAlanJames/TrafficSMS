"""Typed assessment of nationwide TrafficSMS request quality."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


QualityLevel = Literal["high", "medium", "low", "unsupported", "unknown"]
CoverageStatus = Literal[
    "covered_by_internal_data", "provider_ready", "no_active_internal_data",
    "unsupported_region", "ambiguous_location", "missing_location", "provider_unavailable",
]


@dataclass(frozen=True, slots=True)
class TrafficQualityAssessment:
    """Network-free quality facts used to choose a safe traffic response."""

    request_text: str
    normalized_query: str
    request_type: str
    confidence: float
    quality_level: QualityLevel
    coverage_status: CoverageStatus
    is_supported: bool
    is_ambiguous: bool = False
    requires_more_detail: bool = False
    location_text: str | None = None
    city: str | None = None
    state: str | None = None
    state_abbreviation: str | None = None
    zip_code: str | None = None
    corridor: str | None = None
    highway_system: str | None = None
    highway_number: str | None = None
    direction: str | None = None
    origin_text: str | None = None
    destination_text: str | None = None
    fallback_reason: str = ""
    user_message: str = ""
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)

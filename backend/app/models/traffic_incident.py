"""Normalized traffic incidents with source attribution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


IncidentType = Literal[
    "Accident",
    "Disabled Vehicle",
    "Road Hazard",
    "Lane Closure",
    "Road Closure",
    "Construction",
    "Police Activity",
    "Weather",
    "Fire",
    "Enforcement Camera",
    "Official DUI Notice",
    "General",
]
IncidentSeverity = Literal["LOW", "MODERATE", "HIGH", "SEVERE"]


@dataclass(frozen=True, slots=True)
class TrafficIncident:
    """Provider-neutral incident data used by aggregation and presentation."""

    incident_type: IncidentType
    severity: IncidentSeverity
    location: str
    description: str
    lanes_affected: int | None = None
    started_at: datetime | None = None
    estimated_clearance: datetime | None = None
    source: str = "Traffic Engine"
    confidence: float = 0.0

    @property
    def category(self) -> IncidentType:
        """Compatibility alias for the Revision 3.2 presentation field."""

        return self.incident_type

    @property
    def road_name(self) -> str | None:
        """Compatibility alias for the Revision 3.2 presentation field."""

        return self.location or None

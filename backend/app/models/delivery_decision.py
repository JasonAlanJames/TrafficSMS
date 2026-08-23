"""Internal delivery selection data for one-message traffic responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DeliveryType = Literal["SMS", "MMS"]


@dataclass(frozen=True, slots=True)
class DeliveryDecision:
    """A final, internally logged selection of a single SMS or MMS payload."""

    message: str
    delivery_type: DeliveryType
    estimated_segments: int
    character_count: int
    compression_applied: bool
    compression_ratio: float
    truncation_applied: bool
    reason: str

"""Typed health telemetry for a traffic provider."""

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider: str
    healthy: bool
    last_success: datetime | None = None
    last_failure: datetime | None = None
    consecutive_failures: int = 0
    average_latency_ms: int = 0
    success_rate: float = 0.0
    last_refresh: datetime = field(default_factory=lambda: datetime.now(UTC))

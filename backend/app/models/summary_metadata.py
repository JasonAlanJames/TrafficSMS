"""Typed, internal telemetry for deterministic or Bedrock summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


SummarySource = Literal["deterministic", "bedrock"]


@dataclass(frozen=True, slots=True)
class SummaryMetadata:
    summary_attempted: bool = False
    summary_used: bool = False
    provider: str = ""
    model: str = ""
    formatter_version: str = "4.1"
    summary_version: str = "4.1"
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    grounding_verified: bool = True
    hallucination_check_passed: bool = True
    fallback_used: bool = False
    fallback_reason: str = ""
    generation_latency_ms: int = 0
    delivery_type: Literal["SMS", "MMS"] = "SMS"
    summary_source: SummarySource = "deterministic"

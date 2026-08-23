"""Internal delivery selection data for one-message traffic responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    formatter_version: str = "4.1"
    llm_used: bool = False
    provider: str = ""
    model: str = ""
    latency_ms: int = 0
    fallback_reason: str = ""
    summary_source: str = "deterministic"
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    estimated_cost: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    response_time_ms: int = 0
    delivery_strategy: str = "single_message"
    summary_version: str = "4.1"
    grounding_verified: bool = True
    hallucination_check_passed: bool = True
    bedrock_attempted: bool = False
    bedrock_succeeded: bool = False
    bedrock_failure_reason: str = ""
    original_character_count: int = 0
    compressed_character_count: int = 0

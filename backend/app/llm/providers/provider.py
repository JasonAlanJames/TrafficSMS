"""Provider contract for natural-language traffic summaries."""

from __future__ import annotations

from typing import Protocol

from app.models.traffic_summary_request import TrafficSummaryRequest


class TrafficSummaryProvider(Protocol):
    """Summarize an already-computed traffic request without changing its facts."""

    async def summarize(self, request: TrafficSummaryRequest) -> str: ...


class TrafficSummaryProviderError(RuntimeError):
    """Raised when an optional summary provider cannot supply usable output."""

"""Deterministic cleanup and validation for optional Bedrock summaries."""

from __future__ import annotations

import re
import json

from app.models.traffic_summary_request import TrafficSummaryRequest


_WHITESPACE_RE = re.compile(r"\s+")
_REPEATED_PUNCTUATION_RE = re.compile(r"([!?.,])\1+")
_INTRO_RE = re.compile(r"^(?:traffic(?:sms)?\s*(?:update|summary)?\s*[:\-]\s*)", re.I)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


class SummaryFormatter:
    """Clean provider text and reject summaries that omit or alter known facts."""

    def format(
        self,
        summary: str,
        request: TrafficSummaryRequest,
    ) -> str | None:
        """Return a concise grounded summary or None to require deterministic fallback."""

        cleaned = _INTRO_RE.sub("", summary.strip().strip('"'))
        cleaned = _WHITESPACE_RE.sub(" ", cleaned)
        cleaned = _REPEATED_PUNCTUATION_RE.sub(r"\1", cleaned).strip()
        if not cleaned or not self._preserves_critical_facts(cleaned, request):
            return None
        return cleaned

    @staticmethod
    def _preserves_critical_facts(
        summary: str,
        request: TrafficSummaryRequest,
    ) -> bool:
        normalized = summary.lower()
        critical_values = [
            request.travel_time,
            request.delay_minutes,
        ]
        for value in critical_values:
            if value is not None and str(value) not in normalized:
                return False

        if request.severity.lower() not in normalized:
            return False

        allowed_numbers = set(_NUMBER_RE.findall(json.dumps(request.as_prompt_payload())))
        if not set(_NUMBER_RE.findall(summary)).issubset(allowed_numbers):
            return False

        if request.location.lower() not in normalized:
            return False

        for incident in request.incidents[:1]:
            if incident.incident_type.lower() not in normalized:
                return False
        for route in request.alternate_routes[:1]:
            if route.name.lower() not in normalized:
                return False
        return True

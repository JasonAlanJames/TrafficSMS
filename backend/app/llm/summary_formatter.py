"""Deterministic cleanup and validation for optional Bedrock summaries."""

from __future__ import annotations

import re
import json

from app.models.traffic_summary_request import TrafficSummaryRequest


_WHITESPACE_RE = re.compile(r"\s+")
_REPEATED_PUNCTUATION_RE = re.compile(r"([!?.,])\1+")
_INTRO_RE = re.compile(r"^(?:traffic(?:sms)?\s*(?:update|summary)?\s*[:\-]\s*)", re.I)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_MARKDOWN_RE = re.compile(r"(?:\||^\s*[-*+]\s+)", re.MULTILINE)
_ROAD_RE = re.compile(r"\b(?:I|SR|US)-\d{1,3}\b", re.IGNORECASE)
_UNSAFE_DUI_RE = re.compile(r"\b(?:evade|avoid|bypass|dodge|skip)\b.{0,40}\b(?:dui|checkpoint|police)\b", re.IGNORECASE)
_COVERAGE_TERMS = {
    "closure": ("closure", "closed"),
    "lane_closure": ("lane closure", "lane closed"),
    "construction": ("construction", "roadwork", "work zone"),
    "weather": ("weather", "rain", "fog", "snow", "wind", "flood"),
    "camera": ("camera",),
    "dui_notice": ("dui", "checkpoint"),
}
_INCIDENT_TERMS = {
    "accident": ("accident", "collision", "crash"),
    "disabled_vehicle": ("disabled vehicle", "stalled vehicle"),
    "hazard": ("hazard", "debris"),
    "police": ("police activity", "police report"),
}


class SummaryFormatter:
    """Clean provider text and reject summaries that omit or alter known facts."""

    def __init__(self, *, max_output_chars: int = 320) -> None:
        self._max_output_chars = max_output_chars

    def format(
        self,
        summary: str,
        request: TrafficSummaryRequest,
    ) -> str | None:
        """Return a concise grounded summary or None to require deterministic fallback."""

        if not isinstance(summary, str) or _MARKDOWN_RE.search(summary) or _UNSAFE_DUI_RE.search(summary):
            return None
        cleaned = _INTRO_RE.sub("", summary.strip().strip('"'))
        cleaned = _WHITESPACE_RE.sub(" ", cleaned)
        cleaned = _REPEATED_PUNCTUATION_RE.sub(r"\1", cleaned).strip()
        if len(cleaned) > self._max_output_chars or not self._preserves_critical_facts(cleaned, request):
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

        if request.severity.upper() not in {"LOW", "UNKNOWN"} and request.severity.lower() not in normalized:
            return False

        allowed_numbers = set(_NUMBER_RE.findall(json.dumps(request.as_prompt_payload())))
        if not set(_NUMBER_RE.findall(summary)).issubset(allowed_numbers):
            return False

        if request.location.lower() not in normalized:
            return False

        allowed_roads = {
            road.upper()
            for road in _ROAD_RE.findall(json.dumps(request.as_prompt_payload()))
        }
        if not {road.upper() for road in _ROAD_RE.findall(summary)}.issubset(allowed_roads):
            return False

        official_sources = {"official_dui_notice"}
        has_official_source = any(item.source in official_sources for item in request.coverage)
        if "official" in normalized and not has_official_source:
            return False

        for incident in request.incidents[:1]:
            if incident.incident_type.lower() not in normalized:
                return False
        for route in request.alternate_routes[:1]:
            if route.name.lower() not in normalized:
                return False
        for category, terms in _COVERAGE_TERMS.items():
            category_items = [item for item in request.coverage if item.category == category]
            if category_items and not any(term in normalized for term in terms):
                return False
            if not category_items and any(term in normalized for term in terms):
                return False
        available_incident_text = " ".join(
            [incident.incident_type.lower() for incident in request.incidents]
            + [item.category.replace("_", " ") for item in request.coverage]
        )
        for category, terms in _INCIDENT_TERMS.items():
            if category.replace("_", " ") not in available_incident_text and any(term in normalized for term in terms):
                return False
        return True

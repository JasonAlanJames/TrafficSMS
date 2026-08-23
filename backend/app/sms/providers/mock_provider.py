"""Deterministic local provider used until an external LLM is configured."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.sms.entities import extract_traffic_entities
from app.sms.intents import SMSIntent
from app.sms.providers.provider import AIIntentResult, LLMIntentProvider

if TYPE_CHECKING:
    from app.sms.context import SMSContext


_ROUTE_RE = re.compile(r"(?:TRAFFIC\s+)?FROM\s+(.+?)\s+TO\s+(.+)$")
_TO_DESTINATION_RE = re.compile(r"(?:HOW S\s+TRAFFIC|TRAFFIC)\s+TO\s+(.+)$")
_NEAR_RE = re.compile(r"(?:WHAT S\s+)?TRAFFIC\s+LIKE\s+NEAR\s+(.+)$")
_ACCIDENTS_RE = re.compile(r"ANY\s+ACCIDENTS\s+ON\s+(.+)$")
_HIGHWAY_STATUS_RE = re.compile(r"IS\s+(?:THE\s+)?(.+?)\s+BACKED\s+UP$")


class MockLLMIntentProvider(LLMIntentProvider):
    """Map supported conversational phrases to canonical TrafficSMS commands."""

    async def resolve(self, context: SMSContext) -> AIIntentResult:
        """Return a high-confidence local candidate without external API calls."""

        text = (context.resolved_text or context.normalized_text).strip()
        route_match = _ROUTE_RE.fullmatch(text)
        if route_match is not None:
            return self._traffic_result(
                f"TRAFFIC {route_match.group(1).strip()} TO {route_match.group(2).strip()}",
                "Recognized a conversational route request.",
            )

        near_match = _NEAR_RE.fullmatch(text)
        if near_match is not None:
            return self._traffic_result(
                f"TRAFFIC {near_match.group(1).strip()}",
                "Recognized an area traffic request.",
            )

        if text == "HOW LONG WILL IT TAKE TO GET HOME":
            return self._traffic_result(
                "TRAFFIC HOME",
                "Recognized a saved-home traffic request.",
            )

        if text == "HOW S TRAFFIC GOING TO WORK":
            return self._traffic_result(
                "TRAFFIC WORK",
                "Recognized a saved-work traffic request.",
            )

        accidents_match = _ACCIDENTS_RE.fullmatch(text)
        if accidents_match is not None:
            return self._traffic_result(
                f"TRAFFIC {accidents_match.group(1).strip()}",
                "Recognized a highway traffic request.",
            )

        highway_match = _HIGHWAY_STATUS_RE.fullmatch(text)
        if highway_match is not None:
            return self._traffic_result(
                f"TRAFFIC {highway_match.group(1).strip()}",
                "Recognized a highway status request.",
            )

        if text == "IS DISNEYLAND BUSY":
            return self._traffic_result(
                "TRAFFIC DISNEYLAND",
                "Recognized a landmark traffic request.",
            )

        destination_match = _TO_DESTINATION_RE.fullmatch(text)
        if destination_match is not None:
            destination = destination_match.group(1).strip()
            if context.user is not None and context.user.home_location:
                return self._traffic_result(
                    f"TRAFFIC HOME TO {destination}",
                    "Used the subscriber's saved Home location for the route.",
                )
            return AIIntentResult(
                confidence=0.96,
                detected_intent=None,
                entities={"destination": destination},
                reasoning="Captured a route destination and await an origin follow-up.",
                parser_fallback=True,
            )

        return AIIntentResult(
            confidence=0.0,
            detected_intent=None,
            reasoning="No supported conversational traffic pattern matched.",
            parser_fallback=True,
        )

    @staticmethod
    def _traffic_result(command_text: str, reasoning: str) -> AIIntentResult:
        """Build a canonical traffic candidate with structured entities."""

        return AIIntentResult(
            confidence=0.96,
            detected_intent=SMSIntent.TRAFFIC_ROUTE,
            entities=extract_traffic_entities(command_text),
            reasoning=reasoning,
            parser_fallback=True,
            command_text=command_text,
        )

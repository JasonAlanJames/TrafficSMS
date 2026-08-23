"""Structured entity extraction for canonical TrafficSMS commands."""

from __future__ import annotations

import re


_DIRECTION_RE = re.compile(r"\b(NORTH|SOUTH|EAST|WEST)\b")
_HIGHWAY_RE = re.compile(r"\b(?:I|SR)-\d{1,3}\b")
_ROUTE_RE = re.compile(r"^TRAFFIC\s+(.+?)\s+TO\s+(.+)$")
_SAVED_LOCATIONS = {"HOME", "WORK", "GYM", "SCHOOL"}


def extract_traffic_entities(command_text: str) -> dict[str, str]:
    """Extract reusable traffic entities from canonical command text."""

    text = command_text.strip().upper()
    entities: dict[str, str] = {}
    route_match = _ROUTE_RE.fullmatch(text)

    if route_match is not None:
        origin = route_match.group(1).strip()
        destination = route_match.group(2).strip()
        entities.update(
            {
                "origin": origin,
                "destination": destination,
                "route": f"{origin} TO {destination}",
            }
        )
    elif text.startswith("TRAFFIC "):
        target = text.removeprefix("TRAFFIC ").strip()
        if target in _SAVED_LOCATIONS:
            entities["saved_location"] = target
        elif target and _HIGHWAY_RE.search(target) is None:
            entities["city"] = target

    highway_match = _HIGHWAY_RE.search(text)
    if highway_match is not None:
        entities["highway"] = highway_match.group(0)
        entities["corridor"] = highway_match.group(0)

    direction_match = _DIRECTION_RE.search(text)
    if direction_match is not None:
        entities["direction"] = direction_match.group(1)

    if "LOS ANGELES INTERNATIONAL AIRPORT" in text:
        entities["landmark"] = "LOS ANGELES INTERNATIONAL AIRPORT"
    elif "DISNEYLAND" in text:
        entities["landmark"] = "DISNEYLAND"

    return entities

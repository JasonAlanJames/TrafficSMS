"""Short-lived, in-process conversation state for SMS follow-up messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re

from app.sms.intents import SMSIntent


_DIRECTIONS = {
    "NORTH": "NORTH",
    "NORTHBOUND": "NORTH",
    "NB": "NORTH",
    "SOUTH": "SOUTH",
    "SOUTHBOUND": "SOUTH",
    "SB": "SOUTH",
    "EAST": "EAST",
    "EASTBOUND": "EAST",
    "EB": "EAST",
    "WEST": "WEST",
    "WESTBOUND": "WEST",
    "WB": "WEST",
}
_FROM_RE = re.compile(r"^FROM\s+(.+)$")


@dataclass(frozen=True)
class ConversationState:
    """The minimum state needed to resolve one SMS follow-up."""

    command_text: str | None
    entities: dict[str, str]
    expires_at: datetime


@dataclass(frozen=True)
class ConversationResolution:
    """A deterministic follow-up reconstructed from a non-expired state."""

    intent: SMSIntent
    command_text: str
    entities: dict[str, str]


class SMSConversationMemory:
    """Keep bounded per-process SMS context without persistent chat history."""

    def __init__(self, ttl_seconds: int):
        self._ttl_seconds = ttl_seconds
        self._states: dict[str, ConversationState] = {}

    def get(
        self,
        phone_number: str,
        now: datetime,
    ) -> ConversationState | None:
        """Return non-expired state and discard expired entries."""

        state = self._states.get(phone_number)
        if state is None:
            return None
        if self._as_utc(state.expires_at) <= self._as_utc(now):
            self._states.pop(phone_number, None)
            return None
        return state

    def record(
        self,
        *,
        phone_number: str,
        command_text: str | None,
        entities: dict[str, str],
        timestamp: datetime,
    ) -> ConversationState:
        """Store only the latest command interpretation until the TTL expires."""

        state = ConversationState(
            command_text=command_text,
            entities=dict(entities),
            expires_at=self._as_utc(timestamp) + timedelta(seconds=self._ttl_seconds),
        )
        self._states[phone_number] = state
        return state

    def resolve_follow_up(
        self,
        *,
        phone_number: str,
        normalized_text: str,
        timestamp: datetime,
    ) -> ConversationResolution | None:
        """Resolve direction and route-origin follow-ups from recent state."""

        state = self.get(phone_number, timestamp)
        if state is None:
            return None

        direction = _DIRECTIONS.get(normalized_text)
        highway = state.entities.get("highway")
        if direction and highway:
            return ConversationResolution(
                intent=SMSIntent.TRAFFIC_ROUTE,
                command_text=f"TRAFFIC {highway} {direction}",
                entities={"highway": highway, "corridor": highway, "direction": direction},
            )

        origin_match = _FROM_RE.fullmatch(normalized_text)
        destination = state.entities.get("destination")
        if origin_match is not None and destination:
            origin = origin_match.group(1).strip()
            return ConversationResolution(
                intent=SMSIntent.TRAFFIC_ROUTE,
                command_text=f"TRAFFIC {origin} TO {destination}",
                entities={
                    "origin": origin,
                    "destination": destination,
                    "route": f"{origin} TO {destination}",
                },
            )

        return None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        """Treat test-provided naive timestamps as UTC for TTL comparison."""

        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

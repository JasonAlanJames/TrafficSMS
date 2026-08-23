"""Provider contract for natural-language intent candidates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.sms.intents import SMSIntent

if TYPE_CHECKING:
    from app.sms.context import SMSContext


@dataclass(frozen=True)
class AIIntentResult:
    """Structured provider output that deliberately excludes SMS formatting."""

    confidence: float
    detected_intent: SMSIntent | None
    entities: dict[str, str] = field(default_factory=dict)
    reasoning: str = ""
    parser_fallback: bool = True
    command_text: str | None = None


class LLMIntentProvider(ABC):
    """Replaceable asynchronous provider for natural-language intent candidates."""

    @abstractmethod
    async def resolve(self, context: SMSContext) -> AIIntentResult:
        """Return an unformatted intent candidate for an unresolved message."""

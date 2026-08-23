"""Typed data models shared by the SMS engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.sms.intents import SMSIntent


@dataclass(frozen=True)
class SMSParseResult:
    """The normalized representation of one inbound SMS message."""

    raw_text: str
    normalized_text: str
    tokens: tuple[str, ...]
    arguments: tuple[str, ...]


@dataclass(frozen=True)
class SMSResponse:
    """A handler response ready for SMS-specific presentation."""

    success: bool
    intent: SMSIntent
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

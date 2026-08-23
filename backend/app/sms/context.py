"""Request context construction for the SMS engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.repository import BillingRepository
from app.models.entities import User
from app.models.subscription import Subscription
from app.sms.intents import SMSIntent
from app.sms.models import SMSParseResult

if TYPE_CHECKING:
    from app.sms.conversation import ConversationState
    from app.sms.providers.provider import AIIntentResult


@dataclass
class SMSContext:
    """All request state shared by intent-aware SMS command handlers."""

    db: Session
    phone_number: str
    user: User | None
    subscription: Subscription | None
    normalized_text: str
    raw_text: str
    tokens: tuple[str, ...]
    parsed_arguments: tuple[str, ...]
    timestamp: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    resolved_text: str | None = None
    entities: dict[str, str] = field(default_factory=dict)
    conversation: ConversationState | None = None
    ai_result: AIIntentResult | None = None
    intent: SMSIntent | None = None


def build_sms_context(
    *,
    db: Session,
    phone_number: str,
    parsed: SMSParseResult,
    metadata: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> SMSContext:
    """Create one request context with user and subscription state loaded once."""

    user = db.scalar(select(User).where(User.phone_e164 == phone_number))
    subscription = None
    if user is not None:
        subscription = BillingRepository(db).get_subscription_by_user_id(user.id)

    return SMSContext(
        db=db,
        phone_number=phone_number,
        user=user,
        subscription=subscription,
        normalized_text=parsed.normalized_text,
        raw_text=parsed.raw_text,
        tokens=parsed.tokens,
        parsed_arguments=parsed.arguments,
        timestamp=timestamp or datetime.now(UTC),
        metadata=dict(metadata or {}),
    )

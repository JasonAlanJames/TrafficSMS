"""Traffic command handler that bridges to the existing traffic engine."""

from __future__ import annotations

import logging

from app.billing.exceptions import SubscriptionRequiredError, UsageLimitExceededError
from app.billing.repository import BillingRepository
from app.billing.service import BillingService
from app.llm.delivery_formatter import DeliveryFormatter
from app.models.traffic_request import TrafficRequest
from app.services.saved_route_service import SavedRouteService
from app.services.traffic_service import TrafficPreparation, TrafficService
from app.sms.context import SMSContext
from app.sms.handlers.subscription import REGISTRATION_URL
from app.sms.intents import SMSIntent
from app.sms.models import SMSResponse
from app.sms.route_commands import parse_route_alias


logger = logging.getLogger(__name__)


def _onboarding_response(intent: SMSIntent) -> SMSResponse:
    return SMSResponse(
        success=False,
        intent=intent,
        message=(
            "Welcome to TrafficSMS!\n\n"
            "Reply SUBSCRIBE to get started.\n\n"
            "Or visit:\n\n"
            f"{REGISTRATION_URL}"
        ),
    )


def _subscription_response(intent: SMSIntent) -> SMSResponse:
    return SMSResponse(
        success=False,
        intent=intent,
        message=(
            "TrafficSMS requires an active subscription.\n\n"
            "Visit:\n\n"
            f"{REGISTRATION_URL}"
        ),
    )


async def handle_traffic(context: SMSContext) -> SMSResponse:
    """Authorize, account for, and delegate a traffic request to the engine."""

    user = context.user
    intent = context.intent or SMSIntent.TRAFFIC
    if user is None:
        return _onboarding_response(intent)

    billing_service = BillingService(BillingRepository(context.db))
    try:
        billing_context = billing_service.ensure_active_subscription(user)
    except SubscriptionRequiredError:
        return _subscription_response(intent)

    traffic_service = TrafficService()
    saved_route = _resolve_saved_route(context)
    if saved_route is False:
        return SMSResponse(
            success=False,
            intent=intent,
            message="That saved route was not found. Text LIST ROUTES to see your routes.",
        )
    if saved_route is None:
        preparation = traffic_service.prepare_request(context)
    else:
        SavedRouteService(context.db).mark_used(saved_route)
        context.metadata["saved_route_id"] = saved_route.id
        context.metadata["saved_route_alias"] = saved_route.name
        preparation = TrafficPreparation(
            request=TrafficRequest(
                mode="route",
                origin=saved_route.origin_text,
                destination=saved_route.destination_text,
                subscriber_id=user.id,
            )
        )
        if hasattr(traffic_service, "validate_request"):
            preparation = traffic_service.validate_request(preparation.request)
    if preparation.request is None:
        return SMSResponse(
            success=False,
            intent=intent,
            message=preparation.error_message or "Unable to prepare traffic request.",
        )

    try:
        usage_summary = billing_service.record_sms_usage(user)
    except UsageLimitExceededError:
        return SMSResponse(
            success=False,
            intent=intent,
            message=(
                "You have used all included SMS requests for this billing period.\n\n"
                "Manage your subscription or upgrade here:\n\n"
                f"{REGISTRATION_URL}"
            ),
        )

    traffic_result = await traffic_service.build_reply(
        context,
        preparation.request,
    )
    reply = traffic_result.message
    remaining_sms = usage_summary.remaining_sms
    if billing_context.subscription.plan in {"standard", "unlimited"}:
        reply = f"{reply}\n\nSMS remaining this period: {remaining_sms}"

    delivery = DeliveryFormatter().prepare(reply, traffic_result.report)
    logger.info(
        "Traffic response delivery decision",
        extra={
            "delivery_type": delivery.delivery_type,
            "character_count": delivery.character_count,
            "compression_applied": delivery.compression_applied,
            "truncation_applied": delivery.truncation_applied,
            "reason": delivery.reason,
        },
    )

    return SMSResponse(
        success=True,
        intent=intent,
        message=delivery.message,
        metadata={
            **traffic_result.metadata,
            **({
                "saved_route_id": context.metadata["saved_route_id"],
                "saved_route_alias": context.metadata["saved_route_alias"],
            } if "saved_route_id" in context.metadata else {}),
            "remaining_queries": remaining_sms,
            "subscription_level": billing_context.subscription.plan,
            "intent_source": context.metadata.get("intent_source"),
            "entities": dict(context.entities),
        },
    )


def _resolve_saved_route(context: SMSContext):
    """Resolve custom aliases while retaining fixed profile shortcut semantics."""

    if context.user is None:
        return None
    text = context.resolved_text or context.normalized_text
    tokens = text.split()
    service = SavedRouteService(context.db)
    explicit_alias = parse_route_alias(text)
    if explicit_alias:
        return service.get_by_alias(context.user.id, explicit_alias, sms_only=True) or False
    if (
        hasattr(context.db, "scalar")
        and tokens[:1] == ["TRAFFIC"]
        and len(tokens) > 1
        and "TO" not in tokens
    ):
        alias = " ".join(tokens[1:])
        if alias not in {"HOME", "WORK", "GYM", "SCHOOL"}:
            return service.get_by_alias(context.user.id, alias, sms_only=True)
    return None

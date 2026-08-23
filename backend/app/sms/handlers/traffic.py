"""Traffic command handler that bridges to the existing traffic engine."""

from __future__ import annotations

from app.billing.exceptions import SubscriptionRequiredError, UsageLimitExceededError
from app.billing.repository import BillingRepository
from app.billing.service import BillingService
from app.services.traffic_service import TrafficService
from app.sms.context import SMSContext
from app.sms.handlers.subscription import REGISTRATION_URL
from app.sms.intents import SMSIntent
from app.sms.models import SMSResponse


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
    preparation = traffic_service.prepare_request(context)
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

    return SMSResponse(
        success=True,
        intent=intent,
        message=reply,
        metadata={
            **traffic_result.metadata,
            "remaining_queries": remaining_sms,
            "subscription_level": billing_context.subscription.plan,
            "intent_source": context.metadata.get("intent_source"),
            "entities": dict(context.entities),
        },
    )

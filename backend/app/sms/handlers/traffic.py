"""Traffic command handler that bridges to the existing traffic engine."""

from __future__ import annotations

from sqlalchemy import select

from app.billing.exceptions import SubscriptionRequiredError, UsageLimitExceededError
from app.billing.repository import BillingRepository
from app.billing.service import BillingService
from app.models.entities import User
from app.models.traffic_request import TrafficRequest
from app.services.traffic import build_traffic_reply
from app.services.traffic_parser import parse_traffic_command
from app.sms.handlers.subscription import REGISTRATION_URL
from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext, SMSParseResult, SMSResponse


_SAVED_LOCATION_ATTRIBUTES = {
    SMSIntent.TRAFFIC_HOME: "home_location",
    SMSIntent.TRAFFIC_WORK: "work_location",
    SMSIntent.TRAFFIC_GYM: "gym_location",
    SMSIntent.TRAFFIC_SCHOOL: "school_location",
}


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


def _saved_location_request(
    user: User,
    intent: SMSIntent,
) -> TrafficRequest | None:
    attribute = _SAVED_LOCATION_ATTRIBUTES.get(intent)
    location = getattr(user, attribute, None) if attribute else None
    if not location:
        return None
    return TrafficRequest(mode="area", area=location, subscriber_id=user.id)


async def handle_traffic(
    parsed: SMSParseResult,
    context: SMSMessageContext,
) -> SMSResponse:
    """Authorize, account for, and delegate a traffic request to the engine."""

    user = context.db.scalar(
        select(User).where(User.phone_e164 == context.from_number)
    )
    intent = context.intent or SMSIntent.TRAFFIC
    if user is None:
        return _onboarding_response(intent)

    billing_service = BillingService(BillingRepository(context.db))
    try:
        billing_context = billing_service.ensure_active_subscription(user)
    except SubscriptionRequiredError:
        return _subscription_response(intent)

    traffic_request = _build_traffic_request(parsed, user, intent)
    if traffic_request is None:
        location_name = intent.value.removeprefix("traffic_").title()
        return SMSResponse(
            success=False,
            intent=intent,
            message=(
                f"Please configure your {location_name} location before using "
                f"TRAFFIC {location_name.upper()}."
            ),
        )

    if traffic_request.mode == "commute":
        if not user.home_location or not user.work_location:
            return SMSResponse(
                success=False,
                intent=intent,
                message=(
                    "Please configure your Home and Work locations before using "
                    "the TRAFFIC commute command."
                ),
            )
        traffic_request.origin = user.home_location
        traffic_request.destination = user.work_location

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

    reply = await build_traffic_reply(
        db=context.db,
        request=traffic_request,
        user=user,
    )
    remaining_sms = usage_summary.remaining_sms
    if billing_context.subscription.plan in {"standard", "unlimited"}:
        reply = f"{reply}\n\nSMS remaining this period: {remaining_sms}"

    return SMSResponse(
        success=True,
        intent=intent,
        message=reply,
        metadata={
            "remaining_queries": remaining_sms,
            "subscription_level": billing_context.subscription.plan,
        },
    )


def _build_traffic_request(
    parsed: SMSParseResult,
    user: User,
    intent: SMSIntent,
) -> TrafficRequest | None:
    if intent in _SAVED_LOCATION_ATTRIBUTES:
        return _saved_location_request(user, intent)
    return parse_traffic_command(parsed.normalized_text, subscriber_id=user.id)

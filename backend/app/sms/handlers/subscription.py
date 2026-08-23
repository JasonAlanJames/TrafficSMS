"""Subscription onboarding handler retained for webhook compatibility."""

from app.sms.intents import SMSIntent
from app.sms.context import SMSContext
from app.sms.models import SMSResponse


REGISTRATION_URL = "https://trafficsms.com/sms-opt-in"


async def handle_subscribe(_: SMSContext) -> SMSResponse:
    """Direct a subscriber to the existing web registration flow."""

    return SMSResponse(
        success=True,
        intent=SMSIntent.SUBSCRIBE,
        message=(
            "Thanks for choosing TrafficSMS!\n\n"
            "Complete your subscription at:\n\n"
            f"{REGISTRATION_URL}"
        ),
    )

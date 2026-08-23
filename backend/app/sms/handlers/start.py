"""START command handler."""

from app.sms.intents import SMSIntent
from app.sms.context import SMSContext
from app.sms.models import SMSResponse


async def handle_start(_: SMSContext) -> SMSResponse:
    """Return the carrier-compliance resume acknowledgement."""

    return SMSResponse(
        success=True,
        intent=SMSIntent.START,
        message=(
            "Welcome back to TrafficSMS!\n\n"
            "Your subscription is active.\n\n"
            "Reply TRAFFIC anytime for live traffic.\n\n"
            "Reply HELP for commands."
        ),
    )

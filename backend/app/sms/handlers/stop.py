"""STOP command handler."""

from app.sms.intents import SMSIntent
from app.sms.context import SMSContext
from app.sms.models import SMSResponse


async def handle_stop(_: SMSContext) -> SMSResponse:
    """Return the carrier-compliance opt-out acknowledgement."""

    return SMSResponse(
        success=True,
        intent=SMSIntent.STOP,
        message=(
            "You have been unsubscribed.\n\n"
            "Reply START anytime to resume service."
        ),
    )

"""STOP command handler."""

from app.sms.intents import SMSIntent
from app.sms.consent import SMSConsentService
from app.sms.context import SMSContext
from app.sms.models import SMSResponse


async def handle_stop(context: SMSContext) -> SMSResponse:
    """Return the carrier-compliance opt-out acknowledgement."""

    SMSConsentService.opt_out(context)

    return SMSResponse(
        success=True,
        intent=SMSIntent.STOP,
        message=(
            "TrafficSMS: You have been unsubscribed. You will receive no further messages.\n\n"
            "Reply START to resubscribe. Reply HELP for help."
        ),
    )

"""START command handler."""

from app.sms.intents import SMSIntent
from app.sms.consent import SMSConsentService
from app.sms.context import SMSContext
from app.sms.handlers.subscription import REGISTRATION_URL
from app.sms.models import SMSResponse


async def handle_start(context: SMSContext) -> SMSResponse:
    """Return the carrier-compliance resume acknowledgement."""

    SMSConsentService.opt_in(context)

    if context.subscription is not None and context.subscription.status == "active":
        message = (
            "TrafficSMS: You are resubscribed. Text TRAFFIC for current traffic. "
            "Reply HELP for help or STOP to unsubscribe."
        )
    else:
        message = (
            "TrafficSMS: You are resubscribed. To activate service, visit "
            f"{REGISTRATION_URL}. Reply HELP for help or STOP to unsubscribe."
        )

    return SMSResponse(
        success=True,
        intent=SMSIntent.START,
        message=message,
    )

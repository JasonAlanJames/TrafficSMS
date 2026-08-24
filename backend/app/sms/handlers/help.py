"""HELP command handler."""

from app.sms.intents import SMSIntent
from app.sms.consent import SMSConsentService
from app.sms.context import SMSContext
from app.sms.models import SMSResponse


async def handle_help(context: SMSContext) -> SMSResponse:
    """Return the supported public SMS commands."""

    SMSConsentService.record_help(context)

    return SMSResponse(
        success=True,
        intent=SMSIntent.HELP,
        message=(
            "TrafficSMS help: Text TRAFFIC, TRAFFIC 92882, ROUTE WORK, or LIST ROUTES "
            "for traffic info. Visit https://trafficsms.com/support. "
            "Reply STOP to unsubscribe."
        ),
    )

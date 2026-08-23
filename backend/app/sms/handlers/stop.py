"""STOP command handler."""

from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext, SMSParseResult, SMSResponse


async def handle_stop(
    _: SMSParseResult,
    __: SMSMessageContext,
) -> SMSResponse:
    """Return the carrier-compliance opt-out acknowledgement."""

    return SMSResponse(
        success=True,
        intent=SMSIntent.STOP,
        message=(
            "You have been unsubscribed.\n\n"
            "Reply START anytime to resume service."
        ),
    )

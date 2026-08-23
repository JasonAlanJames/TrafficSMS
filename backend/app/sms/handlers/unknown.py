"""Fallback command handler."""

from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext, SMSParseResult, SMSResponse


async def handle_unknown(
    _: SMSParseResult,
    __: SMSMessageContext,
) -> SMSResponse:
    """Return the stable fallback response for unsupported commands."""

    return SMSResponse(
        success=False,
        intent=SMSIntent.UNKNOWN,
        message=(
            "Sorry, I didn't understand that command.\n\n"
            "Reply HELP for available commands."
        ),
    )

"""Fallback command handler."""

from app.sms.intents import SMSIntent
from app.sms.context import SMSContext
from app.sms.models import SMSResponse


async def handle_unknown(context: SMSContext) -> SMSResponse:
    """Return the stable fallback response for unsupported commands."""

    if context.metadata.get("typo_correction_rejected"):
        return SMSResponse(
            success=False,
            intent=SMSIntent.UNKNOWN,
            message=(
                "TrafficSMS\n\n"
                "Sorry, I couldn't understand your request.\n\n"
                "Please check your spelling and try again.\n\n"
                "Reply HELP for available commands."
            ),
        )

    return SMSResponse(
        success=False,
        intent=SMSIntent.UNKNOWN,
        message=(
            "Sorry, I didn't understand that command.\n\n"
            "Reply HELP for available commands."
        ),
    )

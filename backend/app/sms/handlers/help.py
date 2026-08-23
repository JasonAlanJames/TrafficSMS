"""HELP command handler."""

from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext, SMSParseResult, SMSResponse


async def handle_help(
    _: SMSParseResult,
    __: SMSMessageContext,
) -> SMSResponse:
    """Return the supported public SMS commands."""

    return SMSResponse(
        success=True,
        intent=SMSIntent.HELP,
        message=(
            "TrafficSMS\n\n"
            "Available Commands:\n\n"
            "TRAFFIC\n"
            "TRAFFIC HOME\n"
            "TRAFFIC WORK\n"
            "HELP\n"
            "STOP\n"
            "START"
        ),
    )

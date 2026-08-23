"""SMS presentation helpers with no command or business logic."""

from __future__ import annotations

import re

from app.sms.models import SMSResponse


MAX_SMS_MESSAGE_LENGTH = 1600
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")


def format_sms_response(
    response: SMSResponse,
    maximum_length: int = MAX_SMS_MESSAGE_LENGTH,
) -> str:
    """Return a readable, bounded SMS string for a handler response."""

    message = response.message.replace("\r\n", "\n").replace("\r", "\n")
    message = _EXCESS_BLANK_LINES_RE.sub("\n\n", message).strip()

    if maximum_length <= 0 or len(message) <= maximum_length:
        return message

    if maximum_length <= 3:
        return message[:maximum_length]

    return f"{message[: maximum_length - 3].rstrip()}..."

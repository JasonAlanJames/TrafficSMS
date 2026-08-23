"""Deterministic SMS intent detection independent of dispatch and handlers."""

from __future__ import annotations

import re

from app.sms.intents import SMSIntent
from app.sms.models import SMSParseResult


_VOTE_COMMAND_RE = re.compile(r"P\d+")
_SAVED_LOCATION_INTENTS = {
    "HOME": SMSIntent.TRAFFIC_HOME,
    "WORK": SMSIntent.TRAFFIC_WORK,
    "GYM": SMSIntent.TRAFFIC_GYM,
    "SCHOOL": SMSIntent.TRAFFIC_SCHOOL,
}
_SIMPLE_INTENTS = {
    "HELP": SMSIntent.HELP,
    "START": SMSIntent.START,
    "STOP": SMSIntent.STOP,
    "SUBSCRIBE": SMSIntent.SUBSCRIBE,
    "POLICE": SMSIntent.POLICE_REPORT,
}


class SMSIntentResolver:
    """Resolve parser output to one typed intent without side effects."""

    def resolve(self, parsed: SMSParseResult) -> SMSIntent:
        """Return the command intent represented by normalized parser output."""

        if not parsed.tokens:
            return SMSIntent.UNKNOWN

        command = parsed.tokens[0]
        simple_intent = _SIMPLE_INTENTS.get(command)
        if simple_intent is not None:
            return simple_intent
        if command == "TRAFFIC":
            return self._resolve_traffic(parsed.arguments)
        if _VOTE_COMMAND_RE.fullmatch(command) and len(parsed.arguments) == 1:
            return SMSIntent.POLICE_VOTE
        return SMSIntent.UNKNOWN

    @staticmethod
    def _resolve_traffic(arguments: tuple[str, ...]) -> SMSIntent:
        if not arguments:
            return SMSIntent.TRAFFIC
        if "TO" in arguments:
            return SMSIntent.TRAFFIC_ROUTE
        return _SAVED_LOCATION_INTENTS.get(arguments[0], SMSIntent.TRAFFIC_ROUTE)

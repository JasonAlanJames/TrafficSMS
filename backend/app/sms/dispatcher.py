"""Intent detection and handler dispatch for inbound SMS messages."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace

from app.sms.handlers.community import handle_police_report, handle_police_vote
from app.sms.handlers.help import handle_help
from app.sms.handlers.start import handle_start
from app.sms.handlers.stop import handle_stop
from app.sms.handlers.subscription import handle_subscribe
from app.sms.handlers.traffic import handle_traffic
from app.sms.handlers.unknown import handle_unknown
from app.sms.intents import SMSIntent
from app.sms.models import SMSMessageContext, SMSParseResult, SMSResponse


SMSHandler = Callable[[SMSParseResult, SMSMessageContext], Awaitable[SMSResponse]]
_VOTE_COMMAND_RE = re.compile(r"P\d+")


class SMSDispatcher:
    """Resolve a parsed message to an intent and invoke its handler."""

    def __init__(self, handlers: Mapping[SMSIntent, SMSHandler] | None = None):
        """Create a dispatcher with optional handler overrides for testing."""

        self._handlers: dict[SMSIntent, SMSHandler] = dict(
            handlers or self._default_handlers()
        )

    async def dispatch(
        self,
        parsed: SMSParseResult,
        context: SMSMessageContext,
    ) -> SMSResponse:
        """Resolve and process one inbound message."""

        intent = self.resolve_intent(parsed)
        handler = self._handlers.get(intent, self._handlers[SMSIntent.UNKNOWN])
        return await handler(parsed, replace(context, intent=intent))

    @staticmethod
    def resolve_intent(parsed: SMSParseResult) -> SMSIntent:
        """Determine intent solely from normalized parser output."""

        if not parsed.tokens:
            return SMSIntent.UNKNOWN

        command = parsed.tokens[0]
        simple_intents = {
            "HELP": SMSIntent.HELP,
            "START": SMSIntent.START,
            "STOP": SMSIntent.STOP,
            "SUBSCRIBE": SMSIntent.SUBSCRIBE,
            "POLICE": SMSIntent.POLICE_REPORT,
        }
        if command in simple_intents:
            return simple_intents[command]
        if command == "TRAFFIC":
            return SMSDispatcher._traffic_intent(parsed.arguments)
        if _VOTE_COMMAND_RE.fullmatch(command) and len(parsed.arguments) == 1:
            return SMSIntent.POLICE_VOTE
        return SMSIntent.UNKNOWN

    @staticmethod
    def _traffic_intent(arguments: tuple[str, ...]) -> SMSIntent:
        if not arguments:
            return SMSIntent.TRAFFIC

        destination_intents = {
            "HOME": SMSIntent.TRAFFIC_HOME,
            "WORK": SMSIntent.TRAFFIC_WORK,
            "GYM": SMSIntent.TRAFFIC_GYM,
            "SCHOOL": SMSIntent.TRAFFIC_SCHOOL,
        }
        return destination_intents.get(arguments[0], SMSIntent.TRAFFIC_ROUTE)

    @staticmethod
    def _default_handlers() -> dict[SMSIntent, SMSHandler]:
        return {
            SMSIntent.HELP: handle_help,
            SMSIntent.START: handle_start,
            SMSIntent.STOP: handle_stop,
            SMSIntent.TRAFFIC: handle_traffic,
            SMSIntent.TRAFFIC_HOME: handle_traffic,
            SMSIntent.TRAFFIC_WORK: handle_traffic,
            SMSIntent.TRAFFIC_GYM: handle_traffic,
            SMSIntent.TRAFFIC_SCHOOL: handle_traffic,
            SMSIntent.TRAFFIC_ROUTE: handle_traffic,
            SMSIntent.SUBSCRIBE: handle_subscribe,
            SMSIntent.POLICE_REPORT: handle_police_report,
            SMSIntent.POLICE_VOTE: handle_police_vote,
            SMSIntent.UNKNOWN: handle_unknown,
        }

"""Intent detection and handler dispatch for inbound SMS messages."""

from __future__ import annotations

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
from app.sms.context import SMSContext
from app.sms.models import SMSResponse


SMSHandler = Callable[[SMSContext], Awaitable[SMSResponse]]


class SMSDispatcher:
    """Invoke the handler selected by the intent resolver."""

    def __init__(self, handlers: Mapping[SMSIntent, SMSHandler] | None = None):
        """Create a dispatcher with optional handler overrides for testing."""

        self._handlers: dict[SMSIntent, SMSHandler] = dict(
            handlers or self._default_handlers()
        )

    async def dispatch(
        self,
        intent: SMSIntent,
        context: SMSContext,
    ) -> SMSResponse:
        """Dispatch an already-resolved intent to its configured handler."""

        handler = self._handlers.get(intent, self._handlers[SMSIntent.UNKNOWN])
        return await handler(replace(context, intent=intent))

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

# TrafficSMS SMS Engine Revision 1

## Overview

Revision 1 establishes the permanent inbound SMS architecture:

```text
Incoming SMS
    -> SMSParser
    -> SMSDispatcher
    -> typed command handler
    -> SMSResponse
    -> SMS formatter
    -> Twilio XML response
```

The Twilio endpoint now performs only signature validation, request-context
construction, SMS-engine invocation, and TwiML serialization. Command routing
and business behavior are outside of FastAPI routes.

## Files Added

- `app/sms/__init__.py`
- `app/sms/intents.py`
- `app/sms/models.py`
- `app/sms/parser.py`
- `app/sms/dispatcher.py`
- `app/sms/formatter.py`
- `app/sms/handlers/help.py`
- `app/sms/handlers/start.py`
- `app/sms/handlers/stop.py`
- `app/sms/handlers/traffic.py`
- `app/sms/handlers/unknown.py`
- `app/sms/handlers/subscription.py`
- `app/sms/handlers/community.py`
- `tests/test_parser.py`
- `tests/test_dispatcher.py`
- `tests/test_handlers.py`

## Files Modified

- `app/api/twilio_webhook.py`
- `app/services/traffic_parser.py`

`app/services/commands.py` was removed because its command tree was migrated
into typed SMS handlers and was no longer reachable.

## Compatibility

The existing traffic engines remain the source of traffic replies. The traffic
handler provides authorization, quota accounting, commute/saved-location
resolution, then calls `build_traffic_reply` without duplicating provider or
traffic-response logic.

The formerly supported `SUBSCRIBE`, police-report, and police-vote messages
remain available as typed compatibility intents. `SR-<number> <direction>` is
also accepted by the existing corridor parser after parser normalization.

## Extension Points

To add a command in Revision 2:

1. Add an `SMSIntent` member.
2. Add a handler under `app/sms/handlers`.
3. Add one dispatcher intent rule and handler-map entry.
4. Add parser, dispatcher, and handler tests as applicable.

The parser must stay normalization-only. The dispatcher owns routing, handlers
own command behavior, and the formatter owns outbound presentation.

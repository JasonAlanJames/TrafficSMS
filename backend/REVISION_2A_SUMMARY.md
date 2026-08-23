# TrafficSMS SMS Engine Revision 2A

## Architecture Changes

Revision 2A separates deterministic intent resolution, request state, traffic
orchestration, and SMS presentation without changing the Twilio webhook
contract or replacing the existing traffic engines.

```text
Incoming SMS
    -> SMSParser
    -> SMSIntentResolver
    -> SMSContext builder
    -> SMSDispatcher
    -> handler
    -> TrafficService
    -> existing traffic engine and LocationResolver
    -> SMS formatter
    -> Twilio XML response
```

`SMSIntentResolver` owns all intent detection. `SMSDispatcher` only maps an
already-resolved `SMSIntent` to a handler. Each handler receives one
`SMSContext`, which holds the request's phone number, loaded user and
subscription, normalized parser output, timestamp, metadata, and database
session.

`TrafficService` owns deterministic traffic request preparation and delegates
all traffic replies to the established `build_traffic_reply` engine. The
existing `LocationResolver` remains the only geocoding boundary and now
consistently supports all four saved profile locations.

## Supported Commands

- `TRAFFIC`
- `TRAFFIC CORONA`, `TRAFFIC RIVERSIDE`, `TRAFFIC ANAHEIM`, `TRAFFIC LAX`
- `TRAFFIC I-15`, `TRAFFIC I-15 NORTH`, `TRAFFIC I-15 SOUTH`
- `TRAFFIC SR-91`, `TRAFFIC SR-91 EAST`, `TRAFFIC SR-91 WEST`
- `TRAFFIC HOME`, `TRAFFIC WORK`, `TRAFFIC GYM`, `TRAFFIC SCHOOL`
- `TRAFFIC HOME TO WORK`, `TRAFFIC CORONA TO LAX`, `TRAFFIC HOME TO LAX`

Highway variants such as `I15`, `I 15`, `I-15`, `SR91`, `SR 91`, and `SR-91`
normalize through the existing stateless SMS parser before they reach the
traffic parser.

## Files Added

- `app/sms/context.py`
- `app/sms/intent_resolver.py`
- `app/services/traffic_service.py`
- `tests/test_intent_resolver.py`
- `tests/test_traffic_service.py`

## Files Modified

- `app/api/twilio_webhook.py`
- `app/sms/__init__.py`
- `app/sms/dispatcher.py`
- `app/sms/models.py`
- `app/sms/handlers/help.py`
- `app/sms/handlers/start.py`
- `app/sms/handlers/stop.py`
- `app/sms/handlers/subscription.py`
- `app/sms/handlers/unknown.py`
- `app/sms/handlers/community.py`
- `app/sms/handlers/traffic.py`
- `app/services/location_resolver.py`
- `tests/test_parser.py`
- `tests/test_dispatcher.py`
- `tests/test_handlers.py`

## Extension Points

1. Add deterministic command classification in `SMSIntentResolver`.
2. Register the matching handler in `SMSDispatcher`.
3. Put traffic-command preparation in `TrafficService`; do not add geocoding
   outside `LocationResolver` or traffic-provider behavior outside the existing
   traffic engine modules.
4. Use `SMSContext` for all handler dependencies and request data.
5. Add focused parser, intent-resolver, dispatcher, service, and handler tests.

Future AI classification can be introduced as a separate resolver strategy
without changing parser, dispatcher, handler, or traffic-service interfaces.

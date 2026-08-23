# TrafficSMS SMS Engine Revision 2B

## Architecture

Revision 2B adds conversational understanding without changing deterministic
command ownership or the existing traffic engines.

```text
Incoming SMS
    -> SMSParser
    -> synonym dictionary
    -> deterministic SMSIntentResolver
       -> accepted deterministic intent -> dispatcher
       -> recent conversation follow-up -> dispatcher
       -> unresolved message -> LLMIntentProvider candidate
           -> accepted above threshold -> canonical command -> dispatcher
           -> rejected or incomplete -> UNKNOWN
    -> handler
    -> TrafficService
    -> existing traffic engine and LocationResolver
    -> formatter
    -> Twilio XML
```

The resolver remains the single routing authority. The dispatcher only invokes
the handler supplied by that resolver. AI output never contains formatted SMS,
never calls the traffic engine directly, and cannot bypass deterministic command
recognition.

## Confidence Flow

1. Existing commands and deterministic synonyms are resolved first.
2. A valid short-lived conversation follow-up is resolved next.
3. Only unresolved messages invoke `LLMIntentProvider`.
4. A provider candidate must have a typed intent, canonical command text, and
   confidence at or above `LLM_INTENT_CONFIDENCE_THRESHOLD`.
5. The resolver validates the provider's canonical command using the same
   deterministic rules before dispatching it.
6. Low-confidence, incomplete, or invalid candidates return `UNKNOWN`.

The default threshold is `0.85`. `SMS_CONVERSATION_TTL_SECONDS` defaults to
`600`. Conversation state is intentionally in-process, bounded to the latest
interpretation per phone number, and discarded on expiry; no persistent chat
history is created.

## Natural Language Support

The local mock provider supports the requested conversational examples,
including traffic to LAX, the 91, nearby cities, Home and Work travel, highway
incident requests, Disneyland, and `Traffic from Corona to Irvine`.

Deterministic aliases include `the 91`, `91 freeway`, `Riverside Freeway`,
`405`, `5 freeway`, `LAX`, and `Disney`. They canonicalize to existing traffic
commands and therefore do not invoke a provider.

## Files Added

- `app/sms/entities.py`
- `app/sms/synonyms.py`
- `app/sms/conversation.py`
- `app/sms/providers/__init__.py`
- `app/sms/providers/provider.py`
- `app/sms/providers/mock_provider.py`
- `tests/test_nlu.py`

## Files Modified

- `app/core/config.py`
- `.env.example`
- `app/api/twilio_webhook.py`
- `app/sms/__init__.py`
- `app/sms/context.py`
- `app/sms/intent_resolver.py`
- `app/sms/handlers/traffic.py`
- `app/services/traffic_service.py`
- `tests/test_intent_resolver.py`
- `tests/test_handlers.py`
- `tests/test_traffic_service.py`

## Future Providers

### Amazon Bedrock

Implement `BedrockIntentProvider(LLMIntentProvider)` with the same async
`resolve(context)` method. It should return `AIIntentResult` containing only a
canonical command candidate, entities, reasoning, and confidence. The resolver
will retain threshold validation and deterministic command revalidation.

### OpenAI

Implement `OpenAIIntentProvider(LLMIntentProvider)` with structured output
mapped into `AIIntentResult`. It must not format SMS responses or call traffic
services. Swapping providers requires resolver configuration only; parser,
dispatcher, handler, and TrafficService interfaces remain unchanged.

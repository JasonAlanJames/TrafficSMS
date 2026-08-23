# TrafficSMS Milestone 4 Summary

## Architecture

Milestone 4 adds an optional presentation-only Bedrock boundary after the
deterministic traffic report is complete:

```text
Traffic sources
  -> TrafficAggregationService
  -> TrafficIntelligenceService
  -> TrafficReport
  -> TrafficSummaryRequest
  -> BedrockProvider (optional)
  -> SummaryFormatter
  -> DeliveryFormatter
  -> DeliveryDecision
  -> existing Twilio delivery boundary
```

The parser, typo correction, entity catalog, resolver, conversation memory,
SMS provider abstraction, webhook, traffic engine, aggregation, intelligence,
and report computation remain authoritative and unchanged. Bedrock cannot
calculate traffic, alter a report, choose a route, or choose a transport.

## Files Added

- `app/models/traffic_summary_request.py`
- `app/models/delivery_decision.py`
- `app/llm/prompts.py`
- `app/llm/prompts/traffic_summary.txt`
- `app/llm/prompts/incident_summary.txt`
- `app/llm/prompts/route_summary.txt`
- `app/llm/providers/provider.py`
- `app/llm/providers/bedrock_provider.py`
- `app/llm/summary_formatter.py`
- `app/llm/delivery_formatter.py`
- `app/llm/traffic_summary_service.py`
- `tests/test_traffic_summary_request.py`
- `tests/test_bedrock_provider.py`
- `tests/test_llm_formatters.py`

## Files Modified

- `app/core/config.py`
- `.env.example`
- `requirements.txt`
- `app/services/traffic_service.py`
- `app/sms/handlers/traffic.py`

## Bedrock Integration

`TrafficSummaryRequest` is the only object supplied to the Bedrock provider.
It contains only the approved traffic facts: location, travel metrics,
congestion, severity, incidents, alternatives, confidence, provenance, report
age, and timestamp. It intentionally excludes database sessions, ORM entities,
users, authentication, Twilio objects, caches, services, diagnostics, and
implementation details.

`BedrockProvider` uses Bedrock's `converse` API with a configurable region,
model ID, timeout, retry count, temperature, maximum tokens, and top-p. The
provider imports `boto3` only when Bedrock is actually enabled. `BEDROCK_ENABLED`
defaults to `false`, so local and test traffic responses make no AWS calls.

## Prompt and Guardrail Strategy

All prompts are external text files in `app/llm/prompts/`. Every template
instructs the model never to invent traffic facts, incidents, closures, times,
alternates, confidence, or provenance; never to estimate or fabricate missing
information; and to explicitly state unavailable information.

`SummaryFormatter` additionally cleans output and verifies it carries the
reported location, required travel and delay values, severity, leading incident
and alternate details when present, and no numeric claims absent from the
sanitized request. Invalid output is rejected in favor of the deterministic
summary.

## Delivery Strategy

`DeliveryFormatter` processes both deterministic and accepted Bedrock text
after the existing handler adds billing usage information. It normalizes
whitespace, attempts safe compression within the configurable SMS threshold,
and otherwise returns one MMS decision. It never emits multipart SMS segments.
Responses beyond the configured one-MMS limit are bounded with an explicit
truncation decision.

`DeliveryDecision` is internal only and records message text, SMS/MMS choice,
one-segment estimate, character count, compression and truncation details, and
reason. The traffic handler logs these fields for cost monitoring and analytics
without transmitting the decision metadata to users. The existing TwiML webhook
remains unchanged as required; a future media-hosting delivery adapter can act
on MMS decisions without changing the report or summary layers.

## Failure Handling and Logging

Bedrock timeouts, retries exhausted, unavailable service, malformed responses,
and summary-guardrail rejection all log only operational metadata and fall back
to deterministic formatting. Users always receive the deterministic traffic
response. Logs record Bedrock attempt failures, accepted/rejected summaries,
and delivery-decision properties, but do not log prompt or response contents.

## Future Conversational Roadmap

Future conversational capabilities should remain presentation-only consumers of
`TrafficSummaryRequest` or a completed `TrafficReport`. New traffic sources
belong before aggregation; deterministic report fields remain the source of
truth. A future Twilio media-hosting adapter can consume `DeliveryDecision` to
deliver selected MMS payloads while preserving the existing inbound webhook and
one-message policy.

## Validation

Focused Milestone 4 coverage passes with 61 tests. It verifies request
sanitization, prompt rendering and guardrails, Bedrock request isolation,
retry and timeout behavior, summary validation, delivery compression,
SMS/MMS decisions, truncation, and deterministic fallback.

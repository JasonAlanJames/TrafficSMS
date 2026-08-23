# TrafficSMS Milestone 4.1 Summary

## Architecture

```text
TrafficReport -> TrafficSummaryRequest -> optional Bedrock -> SummaryFormatter
  -> DeliveryFormatter -> DeliveryDecision -> existing Twilio boundary
```

TrafficReport remains deterministic and canonical. Bedrock receives only the
sanitized request and remains presentation-only. The webhook, parser,
dispatcher, handler contract, and traffic engine are unchanged.

## New Models

- `TrafficFreshness` records source age, live status, generation, processing,
  and refresh timing.
- `SummaryMetadata` records provider/model, grounding, fallback, versions, and
  latency.
- `DeliveryDecision` adds typed delivery, summary, fallback, latency, token,
  character, compression, and Bedrock-attempt telemetry.

## Provenance and Formatting

`TrafficSource` now supports provider identity/version, authority, licensing,
attribution, cache and timing fields, capabilities, and typed metadata.
Traffic intelligence derives freshness only from report sources. The formatter
adds factual attribution and freshness only when those sources exist.

`DeliveryFormatter` copies `SummaryMetadata` into internal decisions and emits
structured telemetry logs. No telemetry is sent to subscribers.

## Validation

Focused coverage validates typed source metadata, report freshness, provider
attribution, freshness formatting, and delivery telemetry propagation.

# TrafficSMS Revision 3.1 Summary

## Scope

Revision 3.1 adds deterministic, typo-tolerant nationwide entity resolution to
the existing SMS pipeline. It does not change the Twilio webhook contract,
traffic-engine implementation, optional AI provider interface, or SMS response
formatting outside the targeted spelling-help response.

## Processing Pipeline

```text
Incoming SMS
  -> existing parser and context builder
  -> TypoCorrectionService
  -> catalog-backed SMSSynonymDictionary
  -> EntityCatalog resolver
  -> existing SMSIntentResolver / deterministic parser
  -> existing dispatcher and traffic service
```

The optional AI provider remains a fallback only for commands that have not
already been resolved or rejected by deterministic command and entity handling.
Recognized traffic commands with an unknown target, and typo candidates that do
not meet the configured confidence threshold, return the existing unknown/help
path without an AI request.

## Typo Correction

`app/sms/typo_correction.py` provides a standalone full
Damerau-Levenshtein implementation and `TypoCorrectionService`. The service
examines only the command token and supports the TrafficSMS command dictionary:
`TRAFFIC`, `HELP`, `START`, `STOP`, `SUBSCRIBE`, and `POLICE`.

Defaults are configured entirely through environment settings:

```env
TYPO_CORRECTION_MAX_EDIT_DISTANCE=2
TYPO_CORRECTION_THRESHOLD=0.80
```

The confidence calculation is `1 - distance / max(command lengths)`. A
correction is applied only when both the maximum edit distance and threshold
are satisfied. Otherwise, a close but low-confidence token receives the
standard spelling-help response rather than a guessed command.

## Nationwide Entity Catalog

`app/sms/entity_catalog.py` is the sole source of SMS aliases and canonical
entity names. It contains all U.S. states, the required cities, airports,
interstates, U.S. routes, state routes, toll roads, landmarks, and national
parks. `app/sms/synonyms.py` delegates alias expansion to this catalog rather
than maintaining a second replacement table.

The catalog preserves structured entity metadata such as `city`, `airport`,
`state`, `interstate`, `us_route`, `state_route`, `toll_road`, `landmark`, and
`national_park`. Route commands retain distinct origin and destination values.
For example, `TRAFFIC FROM MIAMI TO ORLANDO` resolves both endpoints before the
existing traffic service is called.

To add future locations or aliases, add an `EntityDefinition` entry to the
catalog data. No resolver branching or provider prompt update is necessary.

## Files

Added:

- `app/sms/typo_correction.py`
- `app/sms/entity_catalog.py`
- `tests/test_typo_correction.py`
- `tests/test_entity_catalog.py`

Updated:

- `app/core/config.py`
- `.env.example`
- `app/sms/synonyms.py`
- `app/sms/intent_resolver.py`
- `app/sms/handlers/unknown.py`

## Validation

Focused backend coverage validates Damerau-Levenshtein behavior, command typo
correction, low-confidence rejection, catalog aliases, all requested airports
and interstate identifiers, route origin/destination preservation, unresolved
entity rejection, and traffic-service reachability. The focused suite passes
with 125 tests.

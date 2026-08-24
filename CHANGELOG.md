# Changelog

All notable changes to TrafficSMS are documented here.

## [Unreleased] - 2026-08-17

### Added

- Added Revision 5.9 nationwide deterministic traffic-quality classification for city/state, ZIP, interstate, U.S. route, state-route, ambiguous, and unsupported requests.
- Added Revision 5.8 deterministic-first optional Bedrock traffic summarization with bounded incident coverage, grounding validation, SMS output guardrails, metadata, and safe fallback behavior.
- Added Revision 5.7 expanded incident and closure coverage from active community reports, enforcement cameras, official DUI notices, and normalized provider-result data, including corridor-safe fallbacks.
- Added Revision 5.6 custom saved-route automation, including private route persistence, authenticated account APIs, dashboard management, SMS save/list/delete/lookup commands, and migration `9a7c3e6b2d14`.
- Added authentication hardening for resend verification, refresh replay detection, rate limiting, timed lockouts, session listing, single-session revocation, and auth audit events.
- Added profile, password, email, and phone management APIs plus dashboard UI for those account-center actions.
- Added subscription reconciliation, grace-period support, trial-ready billing fields, atomic SMS usage tracking, and richer billing summary payloads.
- Added the `auth_events` table and the Phase 3 hardening migration that normalizes timestamp handling and removes redundant duplicate unique indexes.
- Added expanded backend integration coverage for session controls, replay detection, rate limiting, lockout recovery, profile mutations, reconciliation, grace handling, and invoice payment sync.

### Changed

- Registration still provisions billing customers opportunistically, but auth responses now use consistent JSON error envelopes and stronger status-code handling.
- SMS command processing now honors billing grace periods and the billing service now recalculates web access state as grace windows expire.
- Stripe checkout now tags customer, plan, email, and environment metadata, and the runtime dependency set now installs `pwdlib[argon2]` so Docker boots match the live auth code path.
- The dashboard is now a full SaaS account center for billing, verification, saved places, security controls, and recent device sessions.

### Fixed

- Fixed webhook and reconciliation state drift by updating last-payment timestamps, grace windows, reconciliation timestamps, and billing access flags from Stripe truth.
- Fixed Docker API startup by installing the Argon2 dependency required by `PasswordHash.recommended()`.
- Fixed duplicate-index debt in the schema and hardened production-only app behavior by gating test routes and adding security headers.

### Testing

- Verified backend tests with `pytest -q` using the existing project virtual environment interpreter.
- Verified frontend production output with `npm run build`.
- Verified `alembic upgrade head` against Dockerized PostgreSQL.
- Verified Docker API startup and `GET /health` returning `200 OK`.
- Current result: `26 passed`.

### Follow-Up

- Email verification, password reset, and email-change delivery still need SMTP or transactional email infrastructure.
- Public deployment, monitoring, alerting, backups, and provider-secret rotation remain external operational follow-up items.

## [v0.5.0-alpha] - 2026-08-17

### Added

- Consolidated the project into the production repository on `main`.
- Added Docker-based development infrastructure with PostgreSQL/PostGIS, Redis, FastAPI, and Next.js.
- Added Alembic baseline, auth schema, and production-safe migration repair.
- Added the public SMS opt-in flow and the authentication frontend/backend foundation.

### Fixed

- Repaired Alembic migration behavior so existing TrafficSMS tables are preserved during schema upgrades.

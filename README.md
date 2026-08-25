# TrafficSMS

TrafficSMS is a production-focused SaaS platform for traffic intelligence delivered through SMS and mobile web. The application is built with FastAPI, Next.js, PostgreSQL/PostGIS, Redis, Twilio, and Stripe.

Current release: `v0.5.0-alpha`

## Deployment Smoke Test

After deployment, run `powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test_production.ps1 -FrontendUrl "https://your-site" -BackendUrl "https://your-api"` to check public endpoint availability.

## What is live in this repository

- Authenticated account registration and login
- JWT access tokens with rotating refresh tokens, replay detection, and session version invalidation
- Email verification resend, verification expiration handling, and password reset resend protection
- Configurable transactional SMTP delivery for verification, password reset, and email-change confirmation; disabled by default until explicitly configured
- Login rate limiting, timed account lockouts, unlock logic, and authentication audit events
- Session listing and single-session revocation support
- Profile, password, email, and phone update endpoints
- SMS opt-in registration flow for Twilio compliance
- Production STOP, HELP, and START handling with locally persisted SMS opt-out state
- Expanded incident and closure coverage from active community reports, enforcement cameras, and official DUI notices
- Optional AI-assisted traffic summaries with deterministic traffic facts retained as the source of truth
- Nationwide traffic-quality hardening for city/state, ZIP, and directional U.S. corridor requests
- Stripe customer creation, checkout, portal access, plan changes, cancellation, reconciliation, and metadata tagging
- Subscription state sync through Stripe webhooks with duplicate-event protection, grace-period handling, and trial-ready fields
- Monthly SMS allowance tracking with atomic usage updates and reset-by-billing-period history
- Account dashboard with live subscription, usage, billing history, verification state, saved places, custom saved routes, security controls, and session management
- Admin subscription inspection endpoint

## Subscription model

- `standard`: 60 SMS requests per billing period
- `unlimited`: 200 SMS requests per billing period
- Both paid plans keep web access available through the dashboard and billing portal

## Billing API

User billing endpoints:

- `GET /billing/pricing`
- `POST /billing/create-checkout-session`
- `POST /billing/customer-portal`
- `GET /billing/subscription`
- `GET /billing/usage`
- `GET /billing/history`
- `POST /billing/reconcile`
- `POST /billing/change-plan`
- `POST /billing/cancel`

Webhook endpoint:

- `POST /webhooks/stripe`

Admin endpoint:

- `GET /admin/users/{user_id}/subscription`

## Custom saved routes

Authenticated users can manage private custom routes through `GET`, `POST`, `PATCH`, and `DELETE /users/me/routes`. Routes store text origins and destinations and can be used without changing fixed Home, Work, Gym, or School locations.

SMS examples:

- `SAVE ROUTE WORK 92882 TO IRVINE`
- `LIST ROUTES`
- `ROUTE WORK`
- `TRAFFIC ROUTE WORK`
- `DELETE ROUTE WORK`

Traffic replies use active internal coverage where available, including accidents, closures, lane closures, construction, hazards, disabled vehicles, weather impacts, police activity, cameras, and official DUI notices. Corridor replies provide a safe no-active-coverage result when no matching internal data exists.

Nationwide examples include `TRAFFIC Phoenix AZ`, `TRAFFIC 10001`, `TRAFFIC I-95 S`, `TRAFFIC US-101 N`, and `TRAFFIC 91 W CA`. Ambiguous or unsupported inputs return concise guidance rather than guessed traffic data.

## SMS Compliance

TrafficSMS processes `STOP`, `STOPALL`, `UNSUBSCRIBE`, `CANCEL`, `END`, `QUIT`, `REVOKE`, `OPTOUT`, `OPT OUT`, `HELP`, `INFO`, `SUPPORT`, `START`, `UNSTOP`, `OPTIN`, `OPT IN`, `YES`, and `IN` before subscription enforcement. STOP records a local opt-out for a matched user; START clears it and records the resume time without replacing the original consent timestamp. Locally opted-out users receive only STOP, HELP, or START compliance responses until they opt in again.

## Optional AI summaries

TrafficSMS formats deterministic, SMS-safe replies first. Amazon Bedrock may be explicitly enabled to improve wording only after the summary passes grounding checks against those facts. Bedrock is disabled by default and unavailable, invalid, unsafe, or ungrounded output always falls back to the deterministic reply.

## Repository layout

```text
TrafficSMS/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |-- auth/
|   |   |-- billing/
|   |   |-- core/
|   |   |-- database/
|   |   |-- models/
|   |   `-- services/
|   |-- tests/
|   |-- .env.example
|   |-- alembic.ini
|   `-- requirements.txt
|-- frontend/
|   |-- app/
|   |-- components/
|   `-- lib/
|-- docker-compose.yml
|-- docker-compose.dev.yml
|-- docker-compose.prod.yml
|-- CHANGELOG.md
|-- PRODUCTION_ROADMAP.md
`-- README.md
```

## Local development

Backend:

```bash
cp backend/.env.example backend/.env
```

Frontend:

```bash
cp frontend/.env.local.example frontend/.env.local
```

Start the stack:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Default local URLs:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Required backend billing configuration

These values must be set for production billing:

- `STRIPE_SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_STANDARD_MONTHLY_PRICE_ID`
- `STRIPE_UNLIMITED_MONTHLY_PRICE_ID`
- `STRIPE_PORTAL_RETURN_URL`
- `ADMIN_EMAILS`

The example env file also includes product ID slots for compatibility, but pricing now resolves from the configured Stripe price IDs.

## Transactional Email

Account lifecycle email is disabled by default in development. It uses standard SMTP configuration, so Mailpit works locally without any Mailpit-specific code.

Production uses Amazon SES SMTP with these non-secret values:

```env
FRONTEND_URL=https://trafficsms.com
SUPPORT_URL=https://trafficsms.com/support
MAIL_FROM=noreply@trafficsms.com
MAIL_FROM_NAME=TrafficSMS
EMAIL_REPLY_TO=support@trafficsms.com
SMTP_HOST=email-smtp.us-west-2.amazonaws.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_SSL=false
SMTP_TIMEOUT_SECONDS=5
```

`MAIL_FROM` is the production sender address, `MAIL_FROM_NAME` is the display name, and `EMAIL_REPLY_TO` is reply-to only. Do not use `EMAIL_FROM_ADDRESS`, `EMAIL_FROM`, or `EMAIL_FROM_NAME` as production sender configuration. SES port `587` uses `SMTP_TLS=true` and `SMTP_SSL=false`.

SMTP credentials and `SECRET_KEY` are secrets: never print, log, document, commit, or expose them. Rotate SES credentials immediately if they are exposed. A production `SECRET_KEY` must have at least 32 characters; generate one with `openssl rand -hex 32`.

Verification emails direct customers to `https://trafficsms.com/verify-email?token=<token>` and password-reset emails direct customers to `https://trafficsms.com/reset-password?token=<token>`. The frontend pages call the existing backend endpoints internally, keeping customers out of raw API and JSON views.

The production web healthcheck intentionally uses `http://127.0.0.1:3000/` rather than `localhost` to avoid an IPv6 loopback resolution failure.

## Database and migrations

TrafficSMS uses PostgreSQL 17, PostGIS, and Alembic. Billing adds these production tables:

- `subscriptions`
- `usage_tracking`
- `billing_events`
- `auth_events`
- `saved_routes`
- local SMS opt-out state on `users`

The Monday, August 17, 2026 hardening migration also:

- adds auth/session hardening columns to `users` and `refresh_tokens`
- removes redundant duplicate unique indexes where matching unique constraints already exist
- normalizes user billing timestamps to timezone-aware PostgreSQL columns
- adds subscription grace-period, trial, and reconciliation fields

Run migrations:

```bash
cd backend
alembic upgrade head
```

## Frontend account experience

The dashboard is now the primary account center and shows:

- Subscription plan and status
- Renewal timing and cancellation state
- Remaining SMS and monthly allowance
- Usage progress with billing-period resets
- Billing history
- Stripe portal access, reconciliation, upgrade, downgrade, and cancellation actions
- Email and phone verification status
- Active device sessions with single-session revocation
- Profile, password, email, and phone management
- Saved home, work, gym, and school locations
- Custom saved-route creation, editing, and deletion alongside derived profile routes

The pricing page now uses the authenticated billing APIs for checkout and plan switching.

## SMS behavior

TrafficSMS supports commands such as:

```text
TRAFFIC
TRAFFIC 92882
POLICE VISIBLE I-15 N NEAR MAGNOLIA
P42 YES
P42 NO
P42 UNSURE
HELP
STOP
START
```

Paid-plan SMS usage is enforced against the active billing period, and replies now include remaining SMS where appropriate.

## Testing and validation

Validated on Monday, August 17, 2026:

- Backend integration suite: `26 passed`
- Frontend production build: `next build` succeeded
- Alembic migration smoke: `alembic upgrade head` succeeded against Dockerized PostgreSQL
- Docker runtime smoke: `docker compose -f docker-compose.dev.yml up -d api` served `GET /health` with `200 OK`

The backend test suite covers authentication plus billing checkout, portal access, reconciliation, webhooks, subscription sync, plan changes, cancellation, usage enforcement, monthly reset behavior, billing history, admin subscription access, session revocation, replay detection, rate limiting, lockout recovery, profile mutation, and contact updates.

## Current roadmap snapshot

- Phase 1 infrastructure: complete
- Phase 2 authentication: complete to production quality, with external email delivery follow-up
- Phase 3 Stripe billing and subscription management: complete to production quality
- Phase 4 traffic engine expansion: in progress
- Phase 5 SMS platform hardening: in progress
- Phase 6 production deployment: planned

## Deployment follow-up

The codebase is ready for the next deployment pass, but production still needs:

- Transactional email delivery for verification, email-change, and reset messages
- Public deployment for Twilio verification evidence and carrier-facing compliance review
- Monitoring, alerting, backups, and CI/CD hardening
- Production-grade `SECRET_KEY`
- Rotation of any previously exposed provider secrets before public rollout

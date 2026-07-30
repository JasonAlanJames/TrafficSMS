# TrafficSMS SaaS MVP

Production-oriented starter for a localized traffic-information subscription platform using FastAPI, Next.js, PostgreSQL/PostGIS, Redis, Twilio SMS, and Stripe Checkout.

## Implemented

- Monthly **$4.99** and annual **$49.99** Stripe subscription checkout.
- Stripe webhook activation and subscription-status synchronization.
- Twilio inbound SMS webhook with request-signature validation outside development.
- `TRAFFIC [area]` traffic summaries through a provider abstraction.
- Peer police reports: visible, hidden, opposite side, and mobile camera.
- `P{id} YES`, `P{id} NO`, and `P{id} UNSURE` confirmations.
- Automatic expiry and confidence/status updates for temporary reports.
- Fixed/mobile enforcement-camera schema with official/community source labeling.
- Official-source-only DUI enforcement notice schema and message inclusion.
- Mobile-first Next.js landing, pricing, and dashboard pages.

## Commands

```text
TRAFFIC
TRAFFIC 92882
TRAFFIC CORONA CA
POLICE VISIBLE I-15 N NEAR MAGNOLIA
POLICE HIDDEN SR-91 W NEAR MAIN
POLICE OTHER SIDE I-15 S NEAR CAJALCO
P42 YES
P42 NO
P42 UNSURE
HELP
STOP
```

## Setup

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
docker compose up
```

Open `http://localhost:3000`; API health is at `http://localhost:8000/health`.

## Stripe

1. Create a recurring product with monthly price `$4.99` and annual price `$49.99`.
2. Put both Price IDs into `backend/.env`.
3. Register `/webhooks/stripe` and subscribe to:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - recommended production additions: `invoice.paid`, `invoice.payment_failed`
4. Put the signing secret into `STRIPE_WEBHOOK_SECRET`.

## Twilio

1. Buy a messaging-capable U.S. number or configure a Messaging Service.
2. Set the incoming-message webhook to `POST https://YOUR-API/webhooks/twilio/inbound`.
3. Complete A2P 10DLC registration before production U.S. 10DLC messaging.
4. Configure opt-in language, HELP, STOP, START, privacy policy, terms, and support information.
5. Set `PUBLIC_BASE_URL` exactly to the externally visible API origin; Twilio signature validation depends on the complete public URL.

## Critical next implementation work

- Replace `DemoTrafficProvider` with state DOT/511 provider adapters.
- Add authentication, phone verification, Stripe customer portal, and account settings.
- Add PostGIS route matching and a commercial routing/travel-time provider.
- Add an official-source ingestion pipeline for DUI notices and camera datasets.
- Add migrations with Alembic instead of `create_all`.
- Add recurring usage reset, rate limiting, audit logs, moderation, abuse detection, and idempotent webhook-event storage.
- Have counsel review jurisdiction-specific data use, messaging disclosures, privacy, and enforcement-camera rules before launch.

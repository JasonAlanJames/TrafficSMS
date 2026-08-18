from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
import stripe
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.dependencies import get_billing_service
from app.billing.exceptions import SubscriptionRequiredError, UsageLimitExceededError
from app.billing.repository import BillingRepository
from app.billing.service import BillingService
from app.core.config import settings
from app.main import app
from app.models.billing_event import BillingEvent
from app.models.entities import User
from app.models.subscription import Subscription
from app.models.usage_tracking import UsageTracking


STANDARD_PRICE_ID = "price_standard_test"
UNLIMITED_PRICE_ID = "price_unlimited_test"
STANDARD_PRODUCT_ID = "prod_standard_test"
UNLIMITED_PRODUCT_ID = "prod_unlimited_test"


def build_phone_number(seed: int) -> str:
    return f"+1714555{seed:04d}"


def register_payload(
    email: str = "driver@example.com",
    phone_number: str = "+17145551234",
) -> dict[str, object]:
    return {
        "email": email,
        "password": "SecurePass1!",
        "phone_number": phone_number,
        "sms_consent": True,
        "marketing_consent": True,
    }


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def create_verified_user(client, db_session: Session, email: str = "driver@example.com") -> User:
    phone_number = build_phone_number(
        1234 + (db_session.scalar(select(func.count()).select_from(User)) or 0)
    )
    response = client.post(
        "/auth/register",
        json=register_payload(email=email, phone_number=phone_number),
    )
    assert response.status_code == 201

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None

    verify_response = client.get(
        "/auth/verify-email",
        params={"token": user.verification_token},
    )
    assert verify_response.status_code == 200

    db_session.refresh(user)
    return user


def login(client, email: str = "driver@example.com", password: str = "SecurePass1!") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
            "remember_me": True,
        },
    )
    assert response.status_code == 200
    return response.json()


class FakeStripeGateway:
    def __init__(self):
        now = int(datetime.now(UTC).timestamp())
        next_month = int((datetime.now(UTC) + timedelta(days=30)).timestamp())
        self.created_customers: list[dict[str, object]] = []
        self.checkout_sessions: list[dict[str, object]] = []
        self.portal_sessions: list[dict[str, object]] = []
        self.modified_subscriptions: list[dict[str, object]] = []
        self.products = {
            STANDARD_PRODUCT_ID: {
                "id": STANDARD_PRODUCT_ID,
                "name": "Standard",
                "description": "60 SMS traffic requests every month.",
            },
            UNLIMITED_PRODUCT_ID: {
                "id": UNLIMITED_PRODUCT_ID,
                "name": "Unlimited",
                "description": "200 SMS traffic requests every month.",
            },
        }
        self.prices = {
            STANDARD_PRICE_ID: {
                "id": STANDARD_PRICE_ID,
                "product": STANDARD_PRODUCT_ID,
                "unit_amount": 599,
                "currency": "usd",
                "recurring": {"interval": "month"},
            },
            UNLIMITED_PRICE_ID: {
                "id": UNLIMITED_PRICE_ID,
                "product": UNLIMITED_PRODUCT_ID,
                "unit_amount": 999,
                "currency": "usd",
                "recurring": {"interval": "month"},
            },
        }
        self.subscriptions = {
            "sub_standard": {
                "id": "sub_standard",
                "customer": "cus_standard",
                "status": "active",
                "cancel_at_period_end": False,
                "canceled_at": None,
                "current_period_start": now,
                "current_period_end": next_month,
                "default_payment_method": {
                    "type": "card",
                    "card": {"brand": "visa", "last4": "4242"},
                },
                "items": {
                    "data": [
                        {
                            "id": "si_standard",
                            "price": {"id": STANDARD_PRICE_ID},
                        }
                    ]
                },
            },
            "sub_unlimited": {
                "id": "sub_unlimited",
                "customer": "cus_unlimited",
                "status": "active",
                "cancel_at_period_end": False,
                "canceled_at": None,
                "current_period_start": now,
                "current_period_end": next_month,
                "default_payment_method": {
                    "type": "card",
                    "card": {"brand": "mastercard", "last4": "4444"},
                },
                "items": {
                    "data": [
                        {
                            "id": "si_unlimited",
                            "price": {"id": UNLIMITED_PRICE_ID},
                        }
                    ]
                },
            },
        }

    def create_customer(
        self,
        *,
        email: str,
        phone: str | None,
        metadata: dict[str, str],
    ):
        customer_id = f"cus_{len(self.created_customers) + 1}"
        payload = {"id": customer_id, "email": email, "phone": phone, "metadata": metadata}
        self.created_customers.append(payload)
        return SimpleNamespace(id=customer_id)

    def retrieve_customer(self, customer_id: str):
        return {"id": customer_id}

    def retrieve_product(self, product_id: str):
        return self.products[product_id]

    def retrieve_price(self, price_id: str):
        return self.prices[price_id]

    def create_checkout_session(self, **kwargs):
        self.checkout_sessions.append(kwargs)
        return SimpleNamespace(
            id=f"cs_{len(self.checkout_sessions)}",
            url="https://checkout.stripe.test/session",
        )

    def create_billing_portal_session(self, **kwargs):
        self.portal_sessions.append(kwargs)
        return SimpleNamespace(
            id=f"bps_{len(self.portal_sessions)}",
            url="https://billing.stripe.test/portal",
        )

    def retrieve_subscription(self, subscription_id: str, **kwargs):
        return self.subscriptions[subscription_id]

    def modify_subscription(self, subscription_id: str, **kwargs):
        subscription = self.subscriptions[subscription_id]
        self.modified_subscriptions.append({"id": subscription_id, "kwargs": kwargs})

        if "cancel_at_period_end" in kwargs:
            subscription["cancel_at_period_end"] = kwargs["cancel_at_period_end"]

        items = kwargs.get("items") or []
        if items:
            subscription["items"]["data"][0]["price"]["id"] = items[0]["price"]

        return subscription

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str,
        secret: str,
    ):
        if signature != "valid-signature" or secret != settings.stripe_webhook_secret:
            raise stripe.error.SignatureVerificationError(
                "Invalid signature",
                signature,
                payload,
            )

        return json.loads(payload.decode("utf-8"))


@pytest.fixture()
def billing_settings():
    original = {
        "stripe_secret_key": settings.stripe_secret_key,
        "stripe_webhook_secret": settings.stripe_webhook_secret,
        "stripe_standard_monthly_price_id": settings.stripe_standard_monthly_price_id,
        "stripe_unlimited_monthly_price_id": settings.stripe_unlimited_monthly_price_id,
        "stripe_portal_return_url": settings.stripe_portal_return_url,
        "admin_emails": settings.admin_emails,
    }

    settings.stripe_secret_key = "sk_test_123"
    settings.stripe_webhook_secret = "whsec_test_123"
    settings.stripe_standard_monthly_price_id = STANDARD_PRICE_ID
    settings.stripe_unlimited_monthly_price_id = UNLIMITED_PRICE_ID
    settings.stripe_portal_return_url = "http://localhost:3000/dashboard"
    settings.admin_emails = ""

    try:
        yield
    finally:
        settings.stripe_secret_key = original["stripe_secret_key"]
        settings.stripe_webhook_secret = original["stripe_webhook_secret"]
        settings.stripe_standard_monthly_price_id = original["stripe_standard_monthly_price_id"]
        settings.stripe_unlimited_monthly_price_id = original["stripe_unlimited_monthly_price_id"]
        settings.stripe_portal_return_url = original["stripe_portal_return_url"]
        settings.admin_emails = original["admin_emails"]


@pytest.fixture()
def fake_stripe_gateway() -> FakeStripeGateway:
    return FakeStripeGateway()


def install_billing_override(db_session: Session, fake_stripe_gateway: FakeStripeGateway) -> None:
    app.dependency_overrides[get_billing_service] = lambda: BillingService(
        BillingRepository(db_session),
        stripe_gateway=fake_stripe_gateway,
    )


def attach_subscription(
    db_session: Session,
    user: User,
    *,
    plan: str = "standard",
    status: str = "active",
    sms_used: int = 0,
    cancel_at_period_end: bool = False,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> Subscription:
    period_start = period_start or datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = period_end or (period_start + timedelta(days=30))
    allowance = 60 if plan == "standard" else 200 if plan == "unlimited" else 0
    price_id = (
        STANDARD_PRICE_ID
        if plan == "standard"
        else UNLIMITED_PRICE_ID
        if plan == "unlimited"
        else None
    )

    subscription = db_session.scalar(
        select(Subscription).where(Subscription.user_id == user.id)
    )

    if subscription is None:
        subscription = Subscription(user_id=user.id)

    subscription.stripe_customer_id = stripe_customer_id or f"cus_{user.id}"
    subscription.stripe_subscription_id = stripe_subscription_id or f"sub_{user.id}"
    subscription.stripe_price_id = price_id
    subscription.plan = plan
    subscription.status = status
    subscription.sms_allowance = allowance
    subscription.current_period_start = period_start
    subscription.current_period_end = period_end
    subscription.cancel_at_period_end = cancel_at_period_end
    subscription.renewal_date = period_end

    db_session.add(subscription)
    db_session.flush()

    usage = db_session.scalar(
        select(UsageTracking)
        .where(UsageTracking.user_id == user.id)
        .order_by(UsageTracking.period_end.desc())
    )

    if usage is None or usage.period_start != period_start:
        usage = UsageTracking(
            user_id=user.id,
            subscription_id=subscription.id,
            period_start=period_start,
            period_end=period_end,
            last_reset_at=period_start,
        )

    usage.subscription_id = subscription.id
    usage.plan = plan
    usage.sms_used = sms_used
    usage.sms_allowance = allowance
    usage.period_start = period_start
    usage.period_end = period_end
    usage.last_reset_at = period_start
    db_session.add(usage)

    user.subscription_plan = plan
    user.subscription_status = status
    user.stripe_customer_id = subscription.stripe_customer_id
    user.stripe_subscription_id = subscription.stripe_subscription_id
    user.stripe_price_id = price_id
    user.current_period_start = period_start
    user.current_period_end = period_end
    user.next_billing_date = period_end
    user.cancel_at_period_end = cancel_at_period_end
    user.monthly_sms_count = sms_used

    db_session.add(user)
    db_session.commit()
    db_session.refresh(subscription)
    db_session.refresh(user)
    return subscription


def test_create_checkout_session_creates_customer_and_event(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    create_verified_user(client, db_session)
    tokens = login(client)
    install_billing_override(db_session, fake_stripe_gateway)

    response = client.post(
        "/billing/create-checkout-session",
        headers=auth_headers(tokens["access_token"]),
        json={"plan": "standard"},
    )

    assert response.status_code == 200
    assert response.json()["url"] == "https://checkout.stripe.test/session"
    assert len(fake_stripe_gateway.created_customers) == 1
    assert len(fake_stripe_gateway.checkout_sessions) == 1
    checkout_payload = fake_stripe_gateway.checkout_sessions[0]
    assert checkout_payload["metadata"]["email"] == "driver@example.com"
    assert checkout_payload["metadata"]["environment"] == settings.app_env
    assert checkout_payload["subscription_data"]["metadata"]["user_id"] == "1"
    assert checkout_payload["success_url"] == "http://localhost:3000/dashboard?subscription=success"
    assert checkout_payload["cancel_url"] == "http://localhost:3000/pricing?cancelled=true"
    assert checkout_payload["allow_promotion_codes"] is False

    user = db_session.scalar(select(User).where(User.email == "driver@example.com"))
    assert user is not None
    assert user.stripe_customer_id == "cus_1"

    events = db_session.scalars(select(BillingEvent)).all()
    assert any(event.event_type == "checkout.session.created" for event in events)


def test_create_customer_portal_returns_redirect_url(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session)
    attach_subscription(
        db_session,
        user,
        stripe_customer_id="cus_existing",
        stripe_subscription_id="sub_standard",
    )
    tokens = login(client)
    install_billing_override(db_session, fake_stripe_gateway)

    response = client.post(
        "/billing/customer-portal",
        headers=auth_headers(tokens["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["url"] == "https://billing.stripe.test/portal"
    assert fake_stripe_gateway.portal_sessions[0]["customer"] == "cus_existing"


def test_webhook_rejects_invalid_signature(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    create_verified_user(client, db_session)
    install_billing_override(db_session, fake_stripe_gateway)

    response = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "bad-signature"},
        content=json.dumps({"id": "evt_bad", "type": "checkout.session.completed", "data": {"object": {}}}),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid Stripe webhook signature."


def test_billing_webhook_alias_accepts_valid_events(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session, email="alias@example.com")
    install_billing_override(db_session, fake_stripe_gateway)

    payload = {
        "id": "evt_checkout_alias",
        "type": "checkout.session.completed",
        "created": int(datetime.now(UTC).timestamp()),
        "data": {
            "object": {
                "metadata": {"user_id": str(user.id), "plan": "standard"},
                "customer": "cus_standard",
                "subscription": "sub_standard",
                "customer_details": {"email": user.email},
            }
        },
    }

    response = client.post(
        "/billing/webhook",
        headers={"Stripe-Signature": "valid-signature"},
        content=json.dumps(payload),
    )

    assert response.status_code == 200
    assert response.json() == {"received": True, "duplicate": False}


def test_checkout_webhook_activates_subscription_and_blocks_duplicates(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session)
    install_billing_override(db_session, fake_stripe_gateway)

    payload = {
        "id": "evt_checkout_completed",
        "type": "checkout.session.completed",
        "created": int(datetime.now(UTC).timestamp()),
        "data": {
            "object": {
                "metadata": {"user_id": str(user.id), "plan": "standard"},
                "customer": "cus_standard",
                "subscription": "sub_standard",
                "customer_details": {"email": user.email},
            }
        },
    }

    first = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "valid-signature"},
        content=json.dumps(payload),
    )
    second = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "valid-signature"},
        content=json.dumps(payload),
    )

    assert first.status_code == 200
    assert first.json() == {"received": True, "duplicate": False}
    assert second.status_code == 200
    assert second.json() == {"received": True, "duplicate": True}

    db_session.refresh(user)
    assert user.subscription_status == "active"
    assert user.subscription_plan == "standard"
    assert user.stripe_subscription_id == "sub_standard"

    subscription = db_session.scalar(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    assert subscription is not None
    assert subscription.status == "active"


def test_subscription_lifecycle_webhooks_update_state(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session, email="lifecycle@example.com")
    attach_subscription(
        db_session,
        user,
        plan="standard",
        stripe_customer_id="cus_standard",
        stripe_subscription_id="sub_standard",
    )
    install_billing_override(db_session, fake_stripe_gateway)

    fake_stripe_gateway.subscriptions["sub_standard"]["status"] = "paused"
    paused = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "valid-signature"},
        content=json.dumps(
            {
                "id": "evt_subscription_paused",
                "type": "customer.subscription.paused",
                "created": int(datetime.now(UTC).timestamp()),
                "data": {"object": fake_stripe_gateway.subscriptions["sub_standard"]},
            }
        ),
    )
    assert paused.status_code == 200

    db_session.refresh(user)
    assert user.subscription_status == "paused"

    fake_stripe_gateway.subscriptions["sub_standard"]["status"] = "active"
    resumed = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "valid-signature"},
        content=json.dumps(
            {
                "id": "evt_subscription_resumed",
                "type": "customer.subscription.resumed",
                "created": int(datetime.now(UTC).timestamp()),
                "data": {"object": fake_stripe_gateway.subscriptions["sub_standard"]},
            }
        ),
    )
    assert resumed.status_code == 200

    db_session.refresh(user)
    assert user.subscription_status == "active"


def test_change_plan_supports_upgrade_and_downgrade(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session)
    attach_subscription(
        db_session,
        user,
        plan="standard",
        stripe_customer_id="cus_standard",
        stripe_subscription_id="sub_standard",
    )
    tokens = login(client)
    install_billing_override(db_session, fake_stripe_gateway)

    upgrade = client.post(
        "/billing/change-plan",
        headers=auth_headers(tokens["access_token"]),
        json={"plan": "unlimited"},
    )
    downgrade = client.post(
        "/billing/change-plan",
        headers=auth_headers(tokens["access_token"]),
        json={"plan": "standard"},
    )

    assert upgrade.status_code == 200
    assert upgrade.json()["plan"] == "unlimited"
    assert downgrade.status_code == 200
    assert downgrade.json()["plan"] == "standard"

    events = db_session.scalars(
        select(BillingEvent).where(BillingEvent.event_type == "subscription.plan_changed")
    ).all()
    assert len(events) == 2


def test_cancel_subscription_marks_period_end_cancellation(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session)
    attach_subscription(
        db_session,
        user,
        plan="standard",
        stripe_customer_id="cus_standard",
        stripe_subscription_id="sub_standard",
    )
    tokens = login(client)
    install_billing_override(db_session, fake_stripe_gateway)

    response = client.post(
        "/billing/cancel",
        headers=auth_headers(tokens["access_token"]),
        json={"cancel_at_period_end": True},
    )

    assert response.status_code == 200
    assert response.json()["cancel_at_period_end"] is True

    db_session.refresh(user)
    assert user.cancel_at_period_end is True


def test_usage_enforcement_and_monthly_reset(db_session: Session):
    user = User(
        email="usage@example.com",
        password_hash="hashed",
        email_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    old_period_start = datetime(2026, 6, 1, tzinfo=UTC)
    old_period_end = datetime(2026, 7, 1, tzinfo=UTC)
    attach_subscription(
        db_session,
        user,
        plan="standard",
        sms_used=60,
        period_start=old_period_start,
        period_end=old_period_end,
    )

    service = BillingService(BillingRepository(db_session))

    with pytest.raises(UsageLimitExceededError):
        service.record_sms_usage(user)

    subscription = db_session.scalar(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    assert subscription is not None
    subscription.current_period_start = datetime(2026, 7, 1, tzinfo=UTC)
    subscription.current_period_end = datetime(2026, 8, 1, tzinfo=UTC)
    subscription.renewal_date = subscription.current_period_end
    db_session.add(subscription)
    db_session.commit()

    usage = service.build_usage_summary(user)
    usage_records = db_session.scalars(
        select(UsageTracking).where(UsageTracking.user_id == user.id)
    ).all()

    assert usage.sms_used == 0
    assert usage.remaining_sms == 60
    assert len(usage_records) == 2


def test_subscription_and_history_endpoints_return_live_billing_state(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session)
    subscription = attach_subscription(
        db_session,
        user,
        plan="unlimited",
        sms_used=12,
        stripe_customer_id="cus_unlimited",
        stripe_subscription_id="sub_unlimited",
    )
    db_session.add(
        BillingEvent(
            user_id=user.id,
            subscription_id=subscription.id,
            stripe_event_id="evt_history_1",
            event_type="invoice.paid",
            status="active",
            source="webhook",
            amount_cents=5900,
            currency="USD",
            message="Invoice paid.",
            payload={"invoice": "in_123"},
            occurred_at=datetime.now(UTC),
        )
    )
    db_session.commit()

    tokens = login(client)
    install_billing_override(db_session, fake_stripe_gateway)

    subscription_response = client.get(
        "/billing/subscription",
        headers=auth_headers(tokens["access_token"]),
    )
    history_response = client.get(
        "/billing/history",
        headers=auth_headers(tokens["access_token"]),
    )

    assert subscription_response.status_code == 200
    assert subscription_response.json()["plan"] == "unlimited"
    assert subscription_response.json()["plan_label"] == "Unlimited Monthly"
    assert subscription_response.json()["status_label"] == "Active"
    assert subscription_response.json()["billing_cycle"] == "Monthly"
    assert subscription_response.json()["payment_method"] == "Mastercard ending in 4444"
    assert subscription_response.json()["stripe_customer_id_masked"] == "cus_...ited"
    assert subscription_response.json()["has_active_subscription"] is True
    assert subscription_response.json()["usage"]["sms_used"] == 12
    assert subscription_response.json()["usage"]["progress_ratio"] == 0.06
    assert subscription_response.json()["web_access_enabled"] is True

    assert history_response.status_code == 200
    assert history_response.json()[0]["event_type"] == "invoice.paid"


def test_admin_subscription_endpoint_returns_target_user_billing_data(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    admin = create_verified_user(client, db_session, email="admin@example.com")
    target = create_verified_user(client, db_session, email="member@example.com")
    attach_subscription(
        db_session,
        target,
        plan="standard",
        sms_used=7,
        stripe_customer_id="cus_member",
        stripe_subscription_id="sub_member",
    )

    settings.admin_emails = admin.email
    tokens = login(client, email=admin.email)
    install_billing_override(db_session, fake_stripe_gateway)

    response = client.get(
        f"/admin/users/{target.id}/subscription",
        headers=auth_headers(tokens["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == target.id
    assert response.json()["plan"] == "standard"
    assert response.json()["sms_used"] == 7


def test_reconcile_endpoint_refreshes_subscription_state(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session, email="reconcile@example.com")
    attach_subscription(
        db_session,
        user,
        plan="standard",
        status="active",
        stripe_customer_id="cus_standard",
        stripe_subscription_id="sub_standard",
    )
    tokens = login(client, email=user.email)
    install_billing_override(db_session, fake_stripe_gateway)

    fake_stripe_gateway.subscriptions["sub_standard"]["status"] = "past_due"
    fake_stripe_gateway.subscriptions["sub_standard"]["trial_end"] = int(
        (datetime.now(UTC) + timedelta(days=7)).timestamp()
    )

    response = client.post(
        "/billing/reconcile",
        headers=auth_headers(tokens["access_token"]),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Subscription reconciled successfully."
    assert body["subscription"]["status"] == "past_due"
    assert body["subscription"]["grace_period_end"] is not None
    assert body["subscription"]["trial_end"] is not None

    subscription = db_session.scalar(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    assert subscription is not None
    assert subscription.last_reconciled_at is not None


def test_grace_period_access_context_respects_grace_window(db_session: Session):
    user = User(
        email="grace@example.com",
        password_hash="hashed",
        email_verified=True,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    subscription = attach_subscription(
        db_session,
        user,
        plan="standard",
        status="past_due",
        stripe_customer_id="cus_grace",
        stripe_subscription_id="sub_grace",
    )
    subscription.grace_period_end = datetime.now(UTC) + timedelta(days=1)
    subscription.web_access_enabled = True
    db_session.add(subscription)
    db_session.commit()

    service = BillingService(BillingRepository(db_session))
    context = service.ensure_active_subscription(user)
    assert context.has_active_subscription is True

    current_summary = service.build_subscription_summary(user)
    assert current_summary.web_access_enabled is True

    subscription.grace_period_end = datetime.now(UTC) - timedelta(minutes=1)
    subscription.web_access_enabled = True
    db_session.add(subscription)
    db_session.commit()

    with pytest.raises(SubscriptionRequiredError):
        service.ensure_active_subscription(user)

    expired_summary = service.build_subscription_summary(user)
    assert expired_summary.web_access_enabled is False


def test_invoice_payment_webhook_updates_last_payment_date(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session, email="invoice@example.com")
    attach_subscription(
        db_session,
        user,
        plan="standard",
        stripe_customer_id="cus_standard",
        stripe_subscription_id="sub_standard",
    )
    install_billing_override(db_session, fake_stripe_gateway)

    created_timestamp = int(datetime.now(UTC).timestamp())
    payload = {
        "id": "evt_invoice_paid",
        "type": "invoice.payment_succeeded",
        "created": created_timestamp,
        "data": {
            "object": {
                "customer": "cus_standard",
                "subscription": "sub_standard",
                "amount_paid": 2900,
                "currency": "usd",
            }
        },
    }

    response = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "valid-signature"},
        content=json.dumps(payload),
    )

    assert response.status_code == 200

    db_session.refresh(user)
    assert user.last_payment_date is not None


def test_invoice_payment_failed_webhook_updates_subscription_state(
    client,
    db_session: Session,
    billing_settings,
    fake_stripe_gateway: FakeStripeGateway,
):
    user = create_verified_user(client, db_session, email="failed@example.com")
    attach_subscription(
        db_session,
        user,
        plan="standard",
        stripe_customer_id="cus_standard",
        stripe_subscription_id="sub_standard",
    )
    install_billing_override(db_session, fake_stripe_gateway)
    fake_stripe_gateway.subscriptions["sub_standard"]["status"] = "past_due"

    response = client.post(
        "/webhooks/stripe",
        headers={"Stripe-Signature": "valid-signature"},
        content=json.dumps(
            {
                "id": "evt_invoice_failed",
                "type": "invoice.payment_failed",
                "created": int(datetime.now(UTC).timestamp()),
                "data": {
                    "object": {
                        "customer": "cus_standard",
                        "subscription": "sub_standard",
                        "amount_due": 599,
                        "currency": "usd",
                    }
                },
            }
        ),
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert user.subscription_status == "past_due"
    assert user.last_payment_date is None

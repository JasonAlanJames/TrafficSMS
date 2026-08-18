from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import stripe

from app.billing.constants import (
    ACTIVE_SUBSCRIPTION_STATUSES,
    PAST_DUE_SUBSCRIPTION_STATUSES,
    get_plan_definition,
)
from app.billing.exceptions import (
    BillingConfigurationError,
    BillingNotFoundError,
    BillingPermissionError,
    InvalidPlanError,
    SubscriptionRequiredError,
    UsageLimitExceededError,
)
from app.billing.repository import BillingRepository
from app.billing.schemas import (
    AdminSubscriptionResponse,
    BillingEventResponse,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    PricingPlanResponse,
    ReconcileSubscriptionResponse,
    SubscriptionSummaryResponse,
    UsageSummaryResponse,
    WebhookReceiptResponse,
)
from app.billing.stripe_gateway import StripeGateway
from app.core.config import settings
from app.models.billing_event import BillingEvent
from app.models.entities import User
from app.models.subscription import Subscription
from app.models.usage_tracking import UsageTracking

logger = logging.getLogger(__name__)


@dataclass
class BillingAccessContext:
    user: User
    subscription: Subscription
    usage: UsageTracking

    @property
    def has_active_subscription(self) -> bool:
        if self.subscription.status in ACTIVE_SUBSCRIPTION_STATUSES:
            return True

        grace_period_end = self.subscription.grace_period_end
        if grace_period_end is None:
            return False

        if grace_period_end.tzinfo is None:
            grace_period_end = grace_period_end.replace(tzinfo=UTC)

        return (
            self.subscription.status in PAST_DUE_SUBSCRIPTION_STATUSES
            and grace_period_end >= datetime.now(UTC)
        )

    @property
    def remaining_sms(self) -> int:
        return max(self.usage.sms_allowance - self.usage.sms_used, 0)

    @property
    def can_send_sms(self) -> bool:
        return self.has_active_subscription and self.remaining_sms > 0

    @property
    def has_unlimited_web_access(self) -> bool:
        return self.has_active_subscription and self.subscription.plan == "unlimited"


class BillingService:
    def __init__(
        self,
        repository: BillingRepository,
        stripe_gateway: StripeGateway | None = None,
    ):
        self.repository = repository
        self.stripe_gateway = stripe_gateway

    @staticmethod
    def _stripe_value(
        value: Any,
        key: str,
        default: Any = None,
    ) -> Any:
        if value is None:
            return default
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _timestamp_to_utc(value: int | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(value, tz=UTC)

    def _require_stripe(self) -> StripeGateway:
        if self.stripe_gateway is None or not settings.stripe_secret_key:
            raise BillingConfigurationError(
                "Stripe billing is not configured."
            )
        return self.stripe_gateway

    def _usage_progress_ratio(
        self,
        used: int,
        allowance: int,
    ) -> float:
        if allowance <= 0:
            return 0.0
        return min(used / allowance, 1.0)

    @staticmethod
    def _mask_identifier(value: str | None) -> str | None:
        if not value:
            return None
        if len(value) <= 8:
            return value
        return f"{value[:4]}...{value[-4:]}"

    @staticmethod
    def _payment_method_label(payment_method: Any) -> str | None:
        if not payment_method:
            return None

        card = BillingService._stripe_value(payment_method, "card")
        if card:
            brand = (BillingService._stripe_value(card, "brand", "") or "").strip()
            last4 = (BillingService._stripe_value(card, "last4", "") or "").strip()
            if brand and last4:
                return f"{brand.title()} ending in {last4}"
            if last4:
                return f"Card ending in {last4}"

        method_type = BillingService._stripe_value(payment_method, "type")
        if method_type:
            return str(method_type).replace("_", " ").title()

        return None

    def _billing_cycle(self, subscription: Subscription) -> str:
        if subscription.plan == "free":
            return "No billing cycle"
        return "Monthly"

    def _subscription_status_label(self, subscription: Subscription) -> str:
        status = (subscription.status or "inactive").replace("_", " ").strip()
        return status.title() if status else "Inactive"

    def _extract_payment_method_from_stripe_subscription(
        self,
        stripe_subscription: Any,
    ) -> str | None:
        payment_method = self._stripe_value(
            stripe_subscription,
            "default_payment_method",
        )
        if payment_method:
            return self._payment_method_label(payment_method)

        latest_invoice = self._stripe_value(stripe_subscription, "latest_invoice") or {}
        payment_intent = self._stripe_value(latest_invoice, "payment_intent") or {}
        payment_method = self._stripe_value(payment_intent, "payment_method")
        return self._payment_method_label(payment_method)

    def _has_subscription_access(
        self,
        subscription: Subscription,
        now: datetime | None = None,
    ) -> bool:
        current_time = now or self._now()

        if subscription.status in ACTIVE_SUBSCRIPTION_STATUSES:
            return True

        grace_period_end = self._as_utc(subscription.grace_period_end)
        return (
            subscription.status in PAST_DUE_SUBSCRIPTION_STATUSES
            and grace_period_end is not None
            and grace_period_end >= current_time
        )

    def _refresh_access_state(
        self,
        subscription: Subscription,
    ) -> Subscription:
        has_access = self._has_subscription_access(subscription)

        if subscription.web_access_enabled == has_access:
            return subscription

        subscription.web_access_enabled = has_access
        return self.repository.save_subscription(subscription)

    def _get_price_id_for_plan(self, plan: str) -> str:
        normalized = plan.strip().lower()

        if normalized == "standard":
            return settings.stripe_standard_monthly_price_id

        if normalized == "unlimited":
            return settings.stripe_unlimited_monthly_price_id

        raise InvalidPlanError("Plan must be either 'standard' or 'unlimited'.")

    def _default_period_bounds(self, now: datetime) -> tuple[datetime, datetime]:
        start = datetime(now.year, now.month, 1, tzinfo=UTC)

        if now.month == 12:
            end = datetime(now.year + 1, 1, 1, tzinfo=UTC)
        else:
            end = datetime(now.year, now.month + 1, 1, tzinfo=UTC)

        return start, end

    def _period_bounds_for_subscription(
        self,
        subscription: Subscription | None,
        now: datetime,
    ) -> tuple[datetime, datetime]:
        if subscription is not None:
            start = self._as_utc(subscription.current_period_start)
            end = self._as_utc(subscription.current_period_end)

            if start is not None and end is not None and end > start:
                return start, end

        return self._default_period_bounds(now)

    def build_pricing(self) -> list[PricingPlanResponse]:
        stripe_gateway = self._require_stripe()

        pricing: list[PricingPlanResponse] = []

        for plan_key in ("standard", "unlimited"):
            fallback_price_id = self._get_price_id_for_plan(plan_key)
            price = stripe_gateway.retrieve_price(fallback_price_id)
            product_ref = self._stripe_value(price, "product")
            product = None

            if isinstance(product_ref, str) and product_ref:
                product = stripe_gateway.retrieve_product(product_ref)

            recurring = self._stripe_value(price, "recurring") or {}
            plan_definition = get_plan_definition(plan_key)

            pricing.append(
                PricingPlanResponse(
                    plan=plan_key,
                    product_id=self._stripe_value(
                        product,
                        "id",
                        product_ref or fallback_price_id,
                    ),
                    price_id=self._stripe_value(price, "id", fallback_price_id),
                    name=self._stripe_value(
                        product,
                        "name",
                        plan_definition.label,
                    ),
                    description=self._stripe_value(product, "description"),
                    price=(self._stripe_value(price, "unit_amount", 0) or 0) / 100,
                    currency=(
                        self._stripe_value(price, "currency", "usd") or "usd"
                    ).upper(),
                    interval=self._stripe_value(recurring, "interval", "month"),
                    sms_allowance=plan_definition.sms_allowance,
                )
            )

        return pricing

    def get_or_create_subscription(self, user: User) -> Subscription:
        existing = self.repository.get_subscription_by_user_id(user.id)

        if existing is not None:
            return self._refresh_access_state(existing)

        plan_definition = get_plan_definition(user.subscription_plan or "free")
        initial_status = user.subscription_status or "inactive"
        subscription = Subscription(
            user_id=user.id,
            stripe_customer_id=user.stripe_customer_id,
            stripe_subscription_id=user.stripe_subscription_id,
            stripe_price_id=user.stripe_price_id,
            plan=user.subscription_plan or "free",
            status=initial_status,
            sms_allowance=plan_definition.sms_allowance,
            web_access_enabled=initial_status in ACTIVE_SUBSCRIPTION_STATUSES,
            current_period_start=self._as_utc(user.current_period_start),
            current_period_end=self._as_utc(user.current_period_end),
            cancel_at_period_end=user.cancel_at_period_end,
            renewal_date=self._as_utc(user.next_billing_date),
        )
        saved = self.repository.save_subscription(subscription)
        return self._refresh_access_state(saved)

    def ensure_stripe_customer(self, user: User) -> str | None:
        subscription = self.get_or_create_subscription(user)

        if user.stripe_customer_id:
            subscription.stripe_customer_id = user.stripe_customer_id
            self.repository.save_subscription(subscription)
            return user.stripe_customer_id

        if subscription.stripe_customer_id:
            user.stripe_customer_id = subscription.stripe_customer_id
            self.repository.save_user(user)
            return subscription.stripe_customer_id

        if not settings.stripe_secret_key:
            return None

        stripe_gateway = self._require_stripe()
        customer = stripe_gateway.create_customer(
            email=user.email,
            phone=user.phone_e164,
            metadata={"user_id": str(user.id)},
        )

        user.stripe_customer_id = customer.id
        subscription.stripe_customer_id = customer.id
        self.repository.save_user(user)
        self.repository.save_subscription(subscription)
        return customer.id

    def provision_customer_for_new_user(self, user: User) -> None:
        try:
            self.ensure_stripe_customer(user)
        except (BillingConfigurationError, stripe.error.StripeError):
            # Registration should continue; billing endpoints will ensure customer creation later.
            return

    def get_or_create_usage_record(
        self,
        user: User,
        subscription: Subscription,
    ) -> UsageTracking:
        now = self._now()
        period_start, period_end = self._period_bounds_for_subscription(
            subscription,
            now,
        )
        plan_definition = get_plan_definition(subscription.plan)
        existing = self.repository.get_usage_record_for_period(
            user_id=user.id,
            period_start=period_start,
        )

        if existing is None:
            existing = self.repository.get_current_usage_record(user.id)

        if existing is not None:
            existing_start = self._as_utc(existing.period_start)
            existing_end = self._as_utc(existing.period_end)

            if (
                existing_start == period_start
                and existing_end == period_end
            ):
                if (
                    existing.sms_allowance != plan_definition.sms_allowance
                    or existing.plan != subscription.plan
                ):
                    existing.sms_allowance = plan_definition.sms_allowance
                    existing.plan = subscription.plan
                    existing.subscription_id = subscription.id
                    self.repository.save_usage_record(existing)
                return existing

        usage_record = UsageTracking(
            user_id=user.id,
            subscription_id=subscription.id,
            plan=subscription.plan,
            sms_used=0,
            sms_allowance=plan_definition.sms_allowance,
            period_start=period_start,
            period_end=period_end,
            last_reset_at=now,
        )
        saved = self.repository.save_usage_record(usage_record)
        user.monthly_sms_count = 0
        self.repository.save_user(user)
        return saved

    def build_usage_summary(self, user: User) -> UsageSummaryResponse:
        subscription = self.get_or_create_subscription(user)
        usage = self.get_or_create_usage_record(user, subscription)

        return UsageSummaryResponse(
            plan=subscription.plan,
            sms_used=usage.sms_used,
            sms_allowance=usage.sms_allowance,
            remaining_sms=max(usage.sms_allowance - usage.sms_used, 0),
            progress_ratio=self._usage_progress_ratio(
                usage.sms_used,
                usage.sms_allowance,
            ),
            period_start=self._as_utc(usage.period_start) or usage.period_start,
            period_end=self._as_utc(usage.period_end) or usage.period_end,
            reset_at=self._as_utc(usage.last_reset_at) or usage.last_reset_at,
        )

    def build_subscription_summary(
        self,
        user: User,
    ) -> SubscriptionSummaryResponse:
        subscription = self.get_or_create_subscription(user)
        subscription = self._refresh_access_state(subscription)
        usage = self.build_usage_summary(user)
        context = self.get_billing_access_context(user)
        payment_method = None

        if self.stripe_gateway is not None and subscription.stripe_subscription_id:
            try:
                stripe_subscription = self.stripe_gateway.retrieve_subscription(
                    subscription.stripe_subscription_id,
                    expand=["default_payment_method", "latest_invoice.payment_intent.payment_method"],
                )
                payment_method = self._extract_payment_method_from_stripe_subscription(
                    stripe_subscription
                )
            except stripe.error.StripeError:
                payment_method = None

        return SubscriptionSummaryResponse(
            plan=subscription.plan,
            plan_label=get_plan_definition(subscription.plan).label,
            status=subscription.status,
            status_label=self._subscription_status_label(subscription),
            has_active_subscription=context.has_active_subscription,
            can_send_sms=context.can_send_sms,
            has_unlimited_web_access=context.has_unlimited_web_access,
            stripe_customer_id=subscription.stripe_customer_id,
            stripe_customer_id_masked=self._mask_identifier(subscription.stripe_customer_id),
            stripe_subscription_id=subscription.stripe_subscription_id,
            stripe_price_id=subscription.stripe_price_id,
            web_access_enabled=subscription.web_access_enabled,
            billing_cycle=self._billing_cycle(subscription),
            cancel_at_period_end=subscription.cancel_at_period_end,
            auto_renew_enabled=not subscription.cancel_at_period_end and subscription.plan != "free",
            current_period_start=self._as_utc(subscription.current_period_start),
            current_period_end=self._as_utc(subscription.current_period_end),
            renewal_date=self._as_utc(subscription.renewal_date),
            grace_period_end=self._as_utc(subscription.grace_period_end),
            trial_end=self._as_utc(subscription.trial_end),
            payment_method=payment_method,
            email_verified=user.email_verified,
            phone_verified=user.phone_verified,
            saved_home_location=user.home_location,
            saved_work_location=user.work_location,
            saved_gym_location=user.gym_location,
            saved_school_location=user.school_location,
            usage=usage,
        )

    def get_billing_access_context(self, user: User) -> BillingAccessContext:
        subscription = self._refresh_access_state(
            self.get_or_create_subscription(user)
        )
        usage = self.get_or_create_usage_record(user, subscription)
        return BillingAccessContext(user=user, subscription=subscription, usage=usage)

    def ensure_active_subscription(self, user: User) -> BillingAccessContext:
        context = self.get_billing_access_context(user)

        if not context.has_active_subscription:
            raise SubscriptionRequiredError(
                "TrafficSMS requires an active subscription."
            )

        return context

    def has_active_subscription(self, user: User) -> bool:
        return self.get_billing_access_context(user).has_active_subscription

    def remaining_sms(self, user: User) -> int:
        return self.get_billing_access_context(user).remaining_sms

    def can_send_sms(self, user: User) -> bool:
        return self.get_billing_access_context(user).can_send_sms

    def has_unlimited_web_access(self, user: User) -> bool:
        return self.get_billing_access_context(user).has_unlimited_web_access

    def enforce_sms_quota(self, user: User) -> BillingAccessContext:
        context = self.ensure_active_subscription(user)

        if context.remaining_sms <= 0:
            raise UsageLimitExceededError(
                "You have reached your monthly SMS allowance."
            )

        return context

    def record_sms_usage(self, user: User, count: int = 1) -> UsageSummaryResponse:
        context = self.enforce_sms_quota(user)

        if context.remaining_sms < count:
            raise UsageLimitExceededError(
                "You have reached your monthly SMS allowance."
            )

        usage = self.repository.record_usage_increment(
            usage_record=context.usage,
            count=count,
            recorded_at=self._now(),
        )

        if usage is None:
            raise UsageLimitExceededError(
                "You have reached your monthly SMS allowance."
            )

        user.monthly_sms_count = usage.sms_used
        self.repository.save_user(user)
        return UsageSummaryResponse(
            plan=context.subscription.plan,
            sms_used=usage.sms_used,
            sms_allowance=usage.sms_allowance,
            remaining_sms=max(usage.sms_allowance - usage.sms_used, 0),
            progress_ratio=self._usage_progress_ratio(
                usage.sms_used,
                usage.sms_allowance,
            ),
            period_start=self._as_utc(usage.period_start) or usage.period_start,
            period_end=self._as_utc(usage.period_end) or usage.period_end,
            reset_at=self._as_utc(usage.last_reset_at) or usage.last_reset_at,
        )

    def _sync_user_from_subscription(self, user: User, subscription: Subscription) -> None:
        user.subscription_plan = subscription.plan
        user.subscription_status = subscription.status
        user.stripe_customer_id = subscription.stripe_customer_id
        user.stripe_subscription_id = subscription.stripe_subscription_id
        user.stripe_price_id = subscription.stripe_price_id
        user.current_period_start = self._as_utc(subscription.current_period_start)
        user.current_period_end = self._as_utc(subscription.current_period_end)
        user.cancel_at_period_end = subscription.cancel_at_period_end
        user.next_billing_date = self._as_utc(subscription.renewal_date)
        user.subscription_updated_at = self._now()
        self.repository.save_user(user)

    def _build_billing_event(
        self,
        *,
        user_id: int | None,
        subscription_id: int | None,
        stripe_event_id: str | None,
        event_type: str,
        status: str | None,
        source: str,
        amount_cents: int | None,
        currency: str | None,
        message: str | None,
        payload: dict[str, Any] | None,
        occurred_at: datetime,
    ) -> BillingEvent:
        return BillingEvent(
            user_id=user_id,
            subscription_id=subscription_id,
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            status=status,
            source=source,
            amount_cents=amount_cents,
            currency=currency,
            message=message,
            payload=payload,
            occurred_at=occurred_at,
        )

    def _log_billing_event(
        self,
        *,
        user_id: int | None,
        subscription_id: int | None,
        stripe_event_id: str | None,
        event_type: str,
        status: str | None,
        source: str,
        amount_cents: int | None = None,
        currency: str | None = None,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
        occurred_at: datetime | None = None,
    ) -> BillingEvent:
        logger.info(
            "Billing event recorded event_type=%s source=%s status=%s user_id=%s stripe_event_id=%s amount_cents=%s currency=%s",
            event_type,
            source,
            status,
            user_id,
            stripe_event_id,
            amount_cents,
            currency,
        )
        event = self._build_billing_event(
            user_id=user_id,
            subscription_id=subscription_id,
            stripe_event_id=stripe_event_id,
            event_type=event_type,
            status=status,
            source=source,
            amount_cents=amount_cents,
            currency=currency,
            message=message,
            payload=payload,
            occurred_at=occurred_at or self._now(),
        )
        return self.repository.save_billing_event(event)

    def create_checkout_session(
        self,
        user: User,
        plan: str,
    ) -> CheckoutSessionResponse:
        stripe_gateway = self._require_stripe()
        requested_plan = plan.strip().lower()
        price_id = self._get_price_id_for_plan(requested_plan)
        customer_id = self.ensure_stripe_customer(user)
        subscription = self.get_or_create_subscription(user)

        if (
            subscription.stripe_subscription_id
            and subscription.plan == requested_plan
            and self._has_subscription_access(subscription)
        ):
            raise InvalidPlanError("This subscription is already active on the requested plan.")

        logger.info(
            "Checkout session creation requested user_id=%s plan=%s customer_id=%s",
            user.id,
            requested_plan,
            customer_id,
        )

        session = stripe_gateway.create_checkout_session(
            mode="subscription",
            customer=customer_id,
            client_reference_id=str(user.id),
            metadata={
                "user_id": str(user.id),
                "plan": requested_plan,
                "email": user.email,
                "environment": settings.app_env,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(user.id),
                    "plan": requested_plan,
                }
            },
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=f"{settings.frontend_url.rstrip('/')}/dashboard?subscription=success",
            cancel_url=f"{settings.frontend_url.rstrip('/')}/pricing?cancelled=true",
            allow_promotion_codes=False,
        )

        self._log_billing_event(
            user_id=user.id,
            subscription_id=subscription.id,
            stripe_event_id=None,
            event_type="checkout.session.created",
            status=subscription.status,
            source="api",
            message=f"Checkout session created for plan {requested_plan}",
            payload={"checkout_session_id": session.id, "price_id": price_id},
        )
        logger.info(
            "Checkout session created user_id=%s plan=%s checkout_session_id=%s",
            user.id,
            requested_plan,
            session.id,
        )

        return CheckoutSessionResponse(url=session.url)

    def create_customer_portal(
        self,
        user: User,
    ) -> CustomerPortalResponse:
        stripe_gateway = self._require_stripe()
        customer_id = self.ensure_stripe_customer(user)

        if not customer_id:
            raise BillingConfigurationError("Unable to create Stripe customer.")

        portal = stripe_gateway.create_billing_portal_session(
            customer=customer_id,
            return_url=settings.STRIPE_PORTAL_RETURN_URL,
        )

        subscription = self.get_or_create_subscription(user)
        self._log_billing_event(
            user_id=user.id,
            subscription_id=subscription.id,
            stripe_event_id=None,
            event_type="customer.portal.created",
            status=subscription.status,
            source="api",
            message="Customer portal session created.",
            payload={"portal_session_id": portal.id},
        )

        return CustomerPortalResponse(url=portal.url)

    def change_plan(
        self,
        user: User,
        plan: str,
    ) -> SubscriptionSummaryResponse:
        stripe_gateway = self._require_stripe()
        subscription = self.get_or_create_subscription(user)

        if not subscription.stripe_subscription_id:
            raise SubscriptionRequiredError(
                "A Stripe subscription is required before changing plans."
            )

        requested_plan = plan.strip().lower()
        if requested_plan == subscription.plan:
            raise InvalidPlanError("Subscription is already on the requested plan.")

        stripe_subscription = stripe_gateway.retrieve_subscription(
            subscription.stripe_subscription_id
        )
        items = stripe_subscription.get("items", {}).get("data", [])

        if not items:
            raise SubscriptionRequiredError("Stripe subscription items are missing.")

        modified = stripe_gateway.modify_subscription(
            subscription.stripe_subscription_id,
            cancel_at_period_end=False,
            proration_behavior="create_prorations",
            items=[
                {
                    "id": items[0]["id"],
                    "price": self._get_price_id_for_plan(requested_plan),
                }
            ],
        )

        self.sync_subscription_from_stripe(
            user=user,
            stripe_subscription=modified,
            source="api",
            history_event_type="subscription.plan_changed",
            message=f"Plan changed to {requested_plan}",
        )

        return self.build_subscription_summary(user)

    def reconcile_subscription(
        self,
        user: User,
    ) -> ReconcileSubscriptionResponse:
        stripe_gateway = self._require_stripe()
        subscription = self.get_or_create_subscription(user)

        if not subscription.stripe_subscription_id:
            raise SubscriptionRequiredError(
                "A Stripe subscription is required before reconciliation."
            )

        stripe_subscription = stripe_gateway.retrieve_subscription(
            subscription.stripe_subscription_id
        )
        self.sync_subscription_from_stripe(
            user=user,
            stripe_subscription=stripe_subscription,
            source="reconcile",
            history_event_type="subscription.reconciled",
            message="Subscription reconciled with Stripe.",
        )
        return ReconcileSubscriptionResponse(
            message="Subscription reconciled successfully.",
            subscription=self.build_subscription_summary(user),
        )

    def cancel_subscription(
        self,
        user: User,
        *,
        cancel_at_period_end: bool,
    ) -> SubscriptionSummaryResponse:
        stripe_gateway = self._require_stripe()
        subscription = self.get_or_create_subscription(user)

        if not subscription.stripe_subscription_id:
            raise SubscriptionRequiredError(
                "A Stripe subscription is required before cancellation."
            )

        modified = stripe_gateway.modify_subscription(
            subscription.stripe_subscription_id,
            cancel_at_period_end=cancel_at_period_end,
        )

        self.sync_subscription_from_stripe(
            user=user,
            stripe_subscription=modified,
            source="api",
            history_event_type="subscription.cancellation_updated",
            message="Subscription cancellation preferences updated.",
        )

        return self.build_subscription_summary(user)

    def sync_subscription_from_stripe(
        self,
        *,
        user: User,
        stripe_subscription: dict[str, Any],
        source: str,
        history_event_type: str | None = None,
        occurred_at: datetime | None = None,
        message: str | None,
    ) -> Subscription:
        subscription = self.get_or_create_subscription(user)
        now = self._now()
        plan = subscription.plan
        items = stripe_subscription.get("items", {}).get("data", [])

        if items:
            price = items[0].get("price", {})
            price_id = price.get("id")
            subscription.stripe_price_id = price_id

            if price_id == settings.stripe_standard_monthly_price_id:
                plan = "standard"
            elif price_id == settings.stripe_unlimited_monthly_price_id:
                plan = "unlimited"

        plan_definition = get_plan_definition(plan)
        subscription.plan = plan_definition.plan
        subscription.status = stripe_subscription.get("status", "inactive")
        subscription.stripe_subscription_id = stripe_subscription.get("id")
        subscription.stripe_customer_id = stripe_subscription.get("customer")
        subscription.sms_allowance = plan_definition.sms_allowance
        subscription.web_access_enabled = (
            subscription.status in ACTIVE_SUBSCRIPTION_STATUSES
        )
        subscription.current_period_start = self._timestamp_to_utc(
            stripe_subscription.get("current_period_start")
        )
        subscription.current_period_end = self._timestamp_to_utc(
            stripe_subscription.get("current_period_end")
        )
        subscription.cancel_at_period_end = stripe_subscription.get(
            "cancel_at_period_end",
            False,
        )
        subscription.canceled_at = self._timestamp_to_utc(
            stripe_subscription.get("canceled_at")
        )
        subscription.trial_end = self._timestamp_to_utc(
            stripe_subscription.get("trial_end")
        )

        if subscription.status in PAST_DUE_SUBSCRIPTION_STATUSES:
            current_grace_period_end = self._as_utc(subscription.grace_period_end)
            if current_grace_period_end is None or current_grace_period_end < now:
                subscription.grace_period_end = now + timedelta(
                    days=settings.billing_grace_period_days
                )
        else:
            subscription.grace_period_end = None

        subscription.last_reconciled_at = now
        subscription.renewal_date = subscription.current_period_end
        subscription.web_access_enabled = self._has_subscription_access(
            subscription,
            now,
        )

        saved = self.repository.save_subscription(subscription)
        usage = self.get_or_create_usage_record(user, saved)
        user.monthly_sms_count = usage.sms_used
        self._sync_user_from_subscription(user, saved)

        if history_event_type:
            self._log_billing_event(
                user_id=user.id,
                subscription_id=saved.id,
                stripe_event_id=None,
                event_type=history_event_type,
                status=saved.status,
                source=source,
                message=message,
                payload=stripe_subscription,
                occurred_at=occurred_at or self._now(),
            )

        return saved

    def get_history(self, user: User) -> list[BillingEventResponse]:
        return [
            BillingEventResponse(
                event_type=event.event_type,
                status=event.status,
                source=event.source,
                amount_cents=event.amount_cents,
                currency=event.currency,
                message=event.message,
                occurred_at=self._as_utc(event.occurred_at) or event.occurred_at,
            )
            for event in self.repository.get_billing_events_for_user(user.id)
        ]

    def get_admin_subscription_summary(
        self,
        *,
        requesting_user: User,
        target_user_id: int,
    ) -> AdminSubscriptionResponse:
        if requesting_user.email.lower() not in settings.ADMIN_EMAILS:
            raise BillingPermissionError()

        target_user = self.repository.get_user_by_id(target_user_id)

        if target_user is None:
            raise BillingNotFoundError("Target user was not found.")

        subscription = self.get_or_create_subscription(target_user)
        subscription = self._refresh_access_state(subscription)
        usage = self.get_or_create_usage_record(target_user, subscription)

        return AdminSubscriptionResponse(
            user_id=target_user.id,
            email=target_user.email,
            plan=subscription.plan,
            status=subscription.status,
            remaining_sms=max(usage.sms_allowance - usage.sms_used, 0),
            sms_allowance=usage.sms_allowance,
            sms_used=usage.sms_used,
            billing_period_start=self._as_utc(usage.period_start) or usage.period_start,
            billing_period_end=self._as_utc(usage.period_end) or usage.period_end,
            renewal_date=self._as_utc(subscription.renewal_date),
            grace_period_end=self._as_utc(subscription.grace_period_end),
            stripe_customer_id=subscription.stripe_customer_id,
            stripe_subscription_id=subscription.stripe_subscription_id,
            cancel_at_period_end=subscription.cancel_at_period_end,
        )

    def process_webhook(
        self,
        *,
        payload: bytes,
        stripe_signature: str,
    ) -> WebhookReceiptResponse:
        stripe_gateway = self._require_stripe()
        event = stripe_gateway.construct_webhook_event(
            payload,
            stripe_signature,
            settings.stripe_webhook_secret,
        )
        event_id = event["id"]
        event_type = event["type"]

        logger.info(
            "Stripe webhook received event_id=%s event_type=%s",
            event_id,
            event_type,
        )

        if self.repository.get_billing_event_by_stripe_event_id(event_id) is not None:
            logger.info(
                "Stripe webhook duplicate ignored event_id=%s event_type=%s",
                event_id,
                event_type,
            )
            return WebhookReceiptResponse(duplicate=True)

        data_object = event["data"]["object"]
        created_at = self._timestamp_to_utc(event.get("created")) or self._now()
        user: User | None = None
        subscription: Subscription | None = None
        message: str | None = None
        supported = True

        if event_type == "checkout.session.completed":
            metadata = data_object.get("metadata", {})
            user_id = metadata.get("user_id")

            if user_id is not None:
                user = self.repository.get_user_by_id(int(user_id))

            if user is None:
                email = (data_object.get("customer_details", {}) or {}).get("email")
                if email:
                    user = self.repository.get_user_by_email(email)

            if user is None:
                client_reference_id = data_object.get("client_reference_id")
                if client_reference_id and str(client_reference_id).isdigit():
                    user = self.repository.get_user_by_id(int(client_reference_id))

            if user is not None:
                user.stripe_customer_id = data_object.get("customer")
                self.repository.save_user(user)
                if data_object.get("subscription"):
                    stripe_subscription = stripe_gateway.retrieve_subscription(
                        data_object["subscription"]
                    )
                    subscription = self.sync_subscription_from_stripe(
                        user=user,
                        stripe_subscription=stripe_subscription,
                        source="webhook",
                        message="Checkout session completed.",
                    )
                    logger.info(
                        "Subscription activated via checkout event_id=%s user_id=%s subscription_id=%s",
                        event_id,
                        user.id,
                        subscription.stripe_subscription_id,
                    )
                message = "Checkout session completed."

        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "customer.subscription.paused",
            "customer.subscription.resumed",
        }:
            customer_id = data_object.get("customer")
            if customer_id:
                subscription = self.repository.get_subscription_by_customer_id(customer_id)

            if subscription is None and data_object.get("id"):
                subscription = self.repository.get_subscription_by_stripe_subscription_id(
                    data_object["id"]
                )

            if subscription is not None:
                user = self.repository.get_user_by_id(subscription.user_id)

            if user is not None:
                subscription = self.sync_subscription_from_stripe(
                    user=user,
                    stripe_subscription=data_object,
                    source="webhook",
                    message=event_type,
                )
                message = event_type
                if event_type in {"customer.subscription.deleted"}:
                    logger.info(
                        "Subscription cancelled event_id=%s user_id=%s subscription_id=%s",
                        event_id,
                        user.id,
                        subscription.stripe_subscription_id,
                    )

        elif event_type in {
            "invoice.payment_succeeded",
            "invoice.payment_failed",
        }:
            customer_id = data_object.get("customer")
            if customer_id:
                subscription = self.repository.get_subscription_by_customer_id(customer_id)

            if subscription is not None:
                user = self.repository.get_user_by_id(subscription.user_id)

            if user is not None and data_object.get("subscription"):
                stripe_subscription = stripe_gateway.retrieve_subscription(
                    data_object["subscription"]
                )
                subscription = self.sync_subscription_from_stripe(
                    user=user,
                    stripe_subscription=stripe_subscription,
                    source="webhook",
                    message=event_type,
                )
                if event_type == "invoice.payment_succeeded":
                    user.last_payment_date = created_at
                    self.repository.save_user(user)
                    logger.info(
                        "Payment succeeded event_id=%s user_id=%s subscription_id=%s",
                        event_id,
                        user.id,
                        subscription.stripe_subscription_id,
                    )
                elif event_type == "invoice.payment_failed":
                    logger.warning(
                        "Payment failed event_id=%s user_id=%s subscription_id=%s",
                        event_id,
                        user.id,
                        subscription.stripe_subscription_id,
                    )
            message = event_type
        else:
            supported = False
            message = "Ignored unsupported Stripe event."
            logger.info(
                "Stripe webhook ignored unsupported event_id=%s event_type=%s",
                event_id,
                event_type,
            )

        if self.repository.get_billing_event_by_stripe_event_id(event_id) is None:
            self._log_billing_event(
                user_id=user.id if user else None,
                subscription_id=subscription.id if subscription else None,
                stripe_event_id=event_id,
                event_type=event_type,
                status=subscription.status if subscription else None,
                source="webhook",
                amount_cents=data_object.get("amount_paid")
                or data_object.get("amount_due")
                or data_object.get("amount_total"),
                currency=(data_object.get("currency") or "").upper() or None,
                message=message,
                payload={"supported": supported, "object": data_object},
                occurred_at=created_at,
            )

        logger.info(
            "Stripe webhook processed event_id=%s event_type=%s supported=%s user_id=%s subscription_id=%s",
            event_id,
            event_type,
            supported,
            user.id if user else None,
            subscription.stripe_subscription_id if subscription else None,
        )
        return WebhookReceiptResponse()

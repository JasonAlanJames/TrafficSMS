from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PricingPlanResponse(BaseModel):
    plan: str
    product_id: str
    price_id: str
    name: str
    description: str | None
    price: float
    currency: str
    interval: str
    sms_allowance: int


class CheckoutSessionRequest(BaseModel):
    plan: str = Field(min_length=3, max_length=32)


class CheckoutSessionResponse(BaseModel):
    url: str


class CustomerPortalResponse(BaseModel):
    url: str


class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True


class ChangePlanRequest(BaseModel):
    plan: str = Field(min_length=3, max_length=32)


class UsageSummaryResponse(BaseModel):
    plan: str
    sms_used: int
    sms_allowance: int
    remaining_sms: int
    progress_ratio: float
    period_start: datetime
    period_end: datetime
    reset_at: datetime


class SubscriptionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan: str
    status: str
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    stripe_price_id: str | None
    web_access_enabled: bool
    cancel_at_period_end: bool
    current_period_start: datetime | None
    current_period_end: datetime | None
    renewal_date: datetime | None
    grace_period_end: datetime | None
    trial_end: datetime | None
    email_verified: bool
    phone_verified: bool
    saved_home_location: str | None
    saved_work_location: str | None
    saved_gym_location: str | None
    saved_school_location: str | None
    usage: UsageSummaryResponse


class BillingEventResponse(BaseModel):
    event_type: str
    status: str | None
    source: str
    amount_cents: int | None
    currency: str | None
    message: str | None
    occurred_at: datetime


class AdminSubscriptionResponse(BaseModel):
    user_id: int
    email: str
    plan: str
    status: str
    remaining_sms: int
    sms_allowance: int
    sms_used: int
    billing_period_start: datetime
    billing_period_end: datetime
    renewal_date: datetime | None
    grace_period_end: datetime | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    cancel_at_period_end: bool


class ReconcileSubscriptionResponse(BaseModel):
    message: str
    subscription: SubscriptionSummaryResponse


class WebhookReceiptResponse(BaseModel):
    received: bool = True
    duplicate: bool = False

from __future__ import annotations

import traceback
import stripe
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_active_user
from app.billing.dependencies import get_admin_billing_user, get_billing_service
from app.billing.exceptions import (
    BillingConfigurationError,
    BillingNotFoundError,
    BillingPermissionError,
    InvalidPlanError,
    SubscriptionRequiredError,
    UsageLimitExceededError,
)
from app.billing.schemas import (
    AdminSubscriptionResponse,
    BillingEventResponse,
    CancelSubscriptionRequest,
    ChangePlanRequest,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CustomerPortalResponse,
    PricingPlanResponse,
    ReconcileSubscriptionResponse,
    SubscriptionSummaryResponse,
    UsageSummaryResponse,
)
from app.billing.service import BillingService
from app.models.entities import User

router = APIRouter(
    prefix="/billing",
    tags=["billing"],
)

admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def _translate_billing_error(exc: Exception) -> HTTPException:
    if isinstance(exc, BillingConfigurationError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    if isinstance(exc, InvalidPlanError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if isinstance(exc, SubscriptionRequiredError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if isinstance(exc, UsageLimitExceededError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    if isinstance(exc, BillingPermissionError):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    if isinstance(exc, BillingNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    if isinstance(exc, stripe.error.StripeError):
        return HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe billing request failed. Please retry shortly.",
        )

    raise exc


@router.get(
    "/pricing",
    response_model=list[PricingPlanResponse],
)
def get_pricing(
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.build_pricing()

    except Exception as exc:
        print("\n================ BILLING DEBUG ================\n")
        print(f"Exception Type : {type(exc).__name__}")
        print(f"Exception      : {repr(exc)}")
        traceback.print_exc()
        print("\n==============================================\n")

        raise


@router.get(
    "/plans",
    response_model=list[PricingPlanResponse],
)
def get_plans(
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.build_pricing()

    except Exception as exc:
        print("\n================ BILLING DEBUG ================\n")
        print(f"Exception Type : {type(exc).__name__}")
        print(f"Exception      : {repr(exc)}")
        traceback.print_exc()
        print("\n==============================================\n")

        raise


@router.post(
    "/create-checkout-session",
    response_model=CheckoutSessionResponse,
)
def create_checkout_session(
    body: CheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.create_checkout_session(current_user, body.plan)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.post(
    "/checkout",
    response_model=CheckoutSessionResponse,
)
def create_checkout_session_legacy(
    body: CheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.create_checkout_session(current_user, body.plan)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.post(
    "/customer-portal",
    response_model=CustomerPortalResponse,
)
def create_customer_portal(
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.create_customer_portal(current_user)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.get(
    "/subscription",
    response_model=SubscriptionSummaryResponse,
)
def get_subscription(
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.build_subscription_summary(current_user)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
)
def get_usage(
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.build_usage_summary(current_user)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.get(
    "/history",
    response_model=list[BillingEventResponse],
)
def get_history(
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.get_history(current_user)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.post(
    "/reconcile",
    response_model=ReconcileSubscriptionResponse,
)
def reconcile_subscription(
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.reconcile_subscription(current_user)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.post(
    "/cancel",
    response_model=SubscriptionSummaryResponse,
)
def cancel_subscription(
    body: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.cancel_subscription(
            current_user,
            cancel_at_period_end=body.cancel_at_period_end,
        )
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@router.post(
    "/change-plan",
    response_model=SubscriptionSummaryResponse,
)
def change_plan(
    body: ChangePlanRequest,
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.change_plan(current_user, body.plan)
    except Exception as exc:
        raise _translate_billing_error(exc) from exc


@admin_router.get(
    "/users/{user_id}/subscription",
    response_model=AdminSubscriptionResponse,
)
def get_admin_subscription_summary(
    user_id: int,
    current_admin: User = Depends(get_admin_billing_user),
    service: BillingService = Depends(get_billing_service),
):
    try:
        return service.get_admin_subscription_summary(
            requesting_user=current_admin,
            target_user_id=user_id,
        )
    except Exception as exc:
        raise _translate_billing_error(exc) from exc

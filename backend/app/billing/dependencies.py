from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.billing.exceptions import BillingPermissionError
from app.billing.repository import BillingRepository
from app.billing.service import BillingAccessContext, BillingService
from app.billing.stripe_gateway import StripeGateway
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import User


def get_billing_service(
    db: Session = Depends(get_db),
) -> BillingService:
    stripe_gateway = None

    if settings.stripe_secret_key:
        stripe_gateway = StripeGateway(settings.stripe_secret_key)

    return BillingService(
        BillingRepository(db),
        stripe_gateway=stripe_gateway,
    )


def get_billing_access_context(
    current_user: User = Depends(get_current_active_user),
    service: BillingService = Depends(get_billing_service),
) -> BillingAccessContext:
    return service.get_billing_access_context(current_user)


def get_admin_billing_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.email.lower() not in settings.ADMIN_EMAILS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=BillingPermissionError.default_message,
        )

    return current_user

from __future__ import annotations

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.billing.dependencies import get_billing_service
from app.billing.exceptions import BillingConfigurationError
from app.billing.schemas import WebhookReceiptResponse
from app.billing.service import BillingService

router = APIRouter(
    prefix="/webhooks/stripe",
    tags=["stripe"],
)


@router.post(
    "",
    response_model=WebhookReceiptResponse,
)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    service: BillingService = Depends(get_billing_service),
):
    payload = await request.body()

    try:
        return service.process_webhook(
            payload=payload,
            stripe_signature=stripe_signature,
        )
    except BillingConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook payload.",
        ) from exc

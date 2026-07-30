from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import stripe

from app.core.config import get_settings

router = APIRouter(
    prefix="/billing",
    tags=["billing"],
)


class CheckoutRequest(BaseModel):
    email: EmailStr
    plan: str


@router.post("/checkout")
def create_checkout(body: CheckoutRequest):
    settings = get_settings()

    stripe.api_key = settings.stripe_secret_key

    plan = body.plan.strip().lower()

    if plan == "standard":
        price_id = settings.stripe_standard_monthly_price_id

    elif plan == "unlimited":
        price_id = settings.stripe_unlimited_monthly_price_id

    else:
        raise HTTPException(
            status_code=400,
            detail="plan must be either 'standard' or 'unlimited'",
        )

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=body.email,

            metadata={
                "plan": plan,
            },

            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=f"{settings.frontend_url}/dashboard?checkout=success",
            cancel_url=f"{settings.frontend_url}/pricing?checkout=canceled",
            allow_promotion_codes=True,
        )

        return {
            "url": session.url
        }

    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe error: {str(exc)}",
        )

@router.get("/pricing")
def get_pricing():
    settings = get_settings()

    stripe.api_key = settings.stripe_secret_key

    try:
        products = [
            settings.stripe_standard_monthly_product_id,
            settings.stripe_unlimited_monthly_product_id,
        ]

        pricing = []

        for product_id in products:
            product = stripe.Product.retrieve(product_id)

            price = stripe.Price.retrieve(product.default_price)

            pricing.append({
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "price": price.unit_amount / 100,
                "currency": price.currency,
                "interval": price.recurring.interval,
                "price_id": price.id,
            })

        return pricing

    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Stripe error: {str(exc)}",
        )

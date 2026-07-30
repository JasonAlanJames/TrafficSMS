from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
import stripe
from datetime import datetime, timezone
from app.core.config import get_settings
from app.core.database import get_db
from app.models.entities import User

router = APIRouter(prefix="/webhooks/stripe", tags=["stripe"])


def determine_plan(price_id: str | None, settings) -> str | None:
    if price_id == settings.stripe_standard_monthly_price_id:
        return "standard"

    if price_id == settings.stripe_unlimited_monthly_price_id:
        return "unlimited"

    return None


@router.post("")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    settings = get_settings(); payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe webhook") from exc
    obj = event["data"]["object"]
    if event["type"] == "checkout.session.completed":
        email = obj.get("customer_details", {}).get("email")

        if email:
            user = db.scalar(
                select(User).where(User.email == email)
            )

            if user is None:
                user = User(email=email)

            user.stripe_customer_id = obj.get("customer")
            user.subscription_status = "active"

            subscription_id = obj.get("subscription")
            if subscription_id:
                user.stripe_subscription_id = subscription_id

            metadata = obj.get("metadata", {})
            if metadata.get("plan"):
                user.subscription_plan = metadata["plan"]

            user.subscription_updated_at = datetime.now(timezone.utc)

            db.add(user)
            db.commit()
    elif event["type"] in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        user = db.scalar(
            select(User).where(
                User.stripe_customer_id == obj.get("customer")
            )
        )

        if user:
            user.subscription_status = obj.get("status", "inactive")
            user.stripe_subscription_id = obj.get("id")

            items = obj.get("items", {}).get("data", [])

            if items:
                price = items[0].get("price", {})
                price_id = price.get("id")

                user.stripe_price_id = price_id
                user.subscription_plan = determine_plan(price_id, settings)

            if obj.get("current_period_start"):
                user.current_period_start = datetime.fromtimestamp(
                    obj["current_period_start"],
                    tz=timezone.utc,
                )

            if obj.get("current_period_end"):
                user.current_period_end = datetime.fromtimestamp(
                    obj["current_period_end"],
                    tz=timezone.utc,
                )
                    
                user.next_billing_date = datetime.fromtimestamp(
                    obj["current_period_end"],
                    tz=timezone.utc,
                )

            user.cancel_at_period_end = obj.get(
                "cancel_at_period_end",
                False,
            )

            if event["type"] != "customer.subscription.deleted":
                user.last_payment_date = datetime.now(timezone.utc)

            user.subscription_updated_at = datetime.now(timezone.utc)

            db.commit()
    return {"received": True}

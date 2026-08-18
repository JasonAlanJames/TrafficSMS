from __future__ import annotations

import stripe


class StripeGateway:
    def __init__(self, api_key: str):
        stripe.api_key = api_key
        self._stripe = stripe

    def create_customer(
        self,
        *,
        email: str,
        phone: str | None,
        metadata: dict[str, str],
    ):
        return self._stripe.Customer.create(
            email=email,
            phone=phone,
            metadata=metadata,
        )

    def retrieve_customer(self, customer_id: str):
        return self._stripe.Customer.retrieve(customer_id)

    def retrieve_product(self, product_id: str):
        return self._stripe.Product.retrieve(product_id)

    def retrieve_price(self, price_id: str):
        return self._stripe.Price.retrieve(price_id)

    def create_checkout_session(self, **kwargs):
        return self._stripe.checkout.Session.create(**kwargs)

    def create_billing_portal_session(self, **kwargs):
        return self._stripe.billing_portal.Session.create(**kwargs)

    def retrieve_subscription(self, subscription_id: str, **kwargs):
        return self._stripe.Subscription.retrieve(subscription_id, **kwargs)

    def modify_subscription(self, subscription_id: str, **kwargs):
        return self._stripe.Subscription.modify(subscription_id, **kwargs)

    def construct_webhook_event(
        self,
        payload: bytes,
        signature: str,
        secret: str,
    ):
        return self._stripe.Webhook.construct_event(payload, signature, secret)

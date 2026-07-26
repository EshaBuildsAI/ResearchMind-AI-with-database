"""
app/services/billing_service.py
Stripe integration for the free->Pro upgrade. Integrating Stripe costs
nothing — you only pay their per-transaction fee on real charges, and
Stripe's test mode (test API keys, test card numbers) is entirely free
for development.

Requires your own Stripe account (free to create) and API keys in .env:
  STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_PRICE_ID_PRO
Without these set, billing endpoints return a clear 503 instead of
crashing, so the rest of the app works fine without a Stripe account.
"""

import logging

import stripe
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User

logger = logging.getLogger("researchmind")


class BillingNotConfigured(Exception):
    pass


def _client():
    if not settings.STRIPE_SECRET_KEY:
        raise BillingNotConfigured(
            "Stripe isn't configured yet. Add STRIPE_SECRET_KEY (and STRIPE_PRICE_ID_PRO) "
            "to your .env — free to get from your Stripe dashboard in test mode."
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(user: User, success_url: str, cancel_url: str) -> str:
    client = _client()
    if not settings.STRIPE_PRICE_ID_PRO:
        raise BillingNotConfigured("STRIPE_PRICE_ID_PRO isn't set — create a Price in your Stripe dashboard.")

    session = client.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
        customer_email=user.email,
        client_reference_id=user.id,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session.url


def create_billing_portal_session(user: User, return_url: str) -> str:
    client = _client()
    if not user.stripe_customer_id:
        raise ValueError("This user has no Stripe customer yet — they haven't subscribed.")
    portal = client.billing_portal.Session.create(customer=user.stripe_customer_id, return_url=return_url)
    return portal.url


def handle_webhook_event(db: Session, payload: bytes, sig_header: str):
    client = _client()
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise BillingNotConfigured("STRIPE_WEBHOOK_SECRET isn't set.")

    event = client.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = data.get("client_reference_id")
        customer_id = data.get("customer")
        subscription_id = data.get("subscription")
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.plan = "pro"
            user.stripe_customer_id = customer_id
            user.stripe_subscription_id = subscription_id
            user.stripe_subscription_status = "active"
            db.commit()
            logger.info(f"User {user_id} upgraded to Pro via Stripe checkout.")

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        customer_id = data.get("customer")
        status = data.get("status")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.stripe_subscription_status = status
            if status in ("canceled", "unpaid", "incomplete_expired") or event_type == "customer.subscription.deleted":
                user.plan = "free"
            elif status == "active":
                user.plan = "pro"
            db.commit()
            logger.info(f"User {user.id} subscription status -> {status} (plan={user.plan}).")

    return {"received": True}

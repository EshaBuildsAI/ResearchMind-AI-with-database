"""
app/routers/billing.py
Stripe checkout for the free->Pro upgrade, billing portal, webhook, and a
usage-summary endpoint the frontend uses to show plan limits/progress.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.schemas import BillingPortalOut, CheckoutSessionOut, UsageSummaryOut
from app.services import billing_service, usage_service
from app.services.billing_service import BillingNotConfigured

router = APIRouter(tags=["billing"])


@router.get("/usage/summary", response_model=UsageSummaryOut)
def usage_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return usage_service.get_usage_summary(db, current_user)


@router.post("/billing/checkout", response_model=CheckoutSessionOut)
def create_checkout(current_user: User = Depends(get_current_user)):
    try:
        url = billing_service.create_checkout_session(
            current_user,
            success_url=f"{settings.FRONTEND_URL}/billing/success",
            cancel_url=f"{settings.FRONTEND_URL}/billing/cancelled",
        )
    except BillingNotConfigured as e:
        raise HTTPException(503, str(e))
    return CheckoutSessionOut(checkout_url=url)


@router.post("/billing/portal", response_model=BillingPortalOut)
def create_portal(current_user: User = Depends(get_current_user)):
    try:
        url = billing_service.create_billing_portal_session(current_user, return_url=f"{settings.FRONTEND_URL}/")
    except BillingNotConfigured as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return BillingPortalOut(portal_url=url)


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        result = billing_service.handle_webhook_event(db, payload, sig_header)
    except BillingNotConfigured as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(400, f"Webhook error: {e}")
    return result

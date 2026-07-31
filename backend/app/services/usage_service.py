"""
app/services/usage_service.py
Tracks per-user daily usage and enforces free/pro plan limits. Backed by
a real DB table (UsageCounter) rather than in-memory, so limits survive
restarts and work correctly across multiple worker processes.
"""

from datetime import datetime, date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Document, UsageCounter, User


def _today_key() -> str:
    return date.today().isoformat()


def get_plan_limits(user: User) -> dict:
    """Read live from settings each call (not baked into a module-level dict
    at import time) so limits can be tuned via env vars without a restart-
    sensitive caching bug. Admins get unlimited (None = no cap) regardless
    of their `plan` field — being an admin shouldn't require also manually
    setting plan='pro'."""
    if user.is_admin:
        return {"documents": None, "chat": None, "agent": None}
    if user.plan == "pro":
        return {
            "documents": settings.PRO_PLAN_MAX_DOCUMENTS,
            "chat": settings.PRO_PLAN_CHAT_PER_DAY,
            "agent": settings.PRO_PLAN_AGENT_PER_DAY,
        }
    return {
        "documents": settings.FREE_PLAN_MAX_DOCUMENTS,
        "chat": settings.FREE_PLAN_CHAT_PER_DAY,
        "agent": settings.FREE_PLAN_AGENT_PER_DAY,
    }


def get_today_count(db: Session, user_id: str, bucket: str) -> int:
    row = (
        db.query(UsageCounter)
        .filter(UsageCounter.user_id == user_id, UsageCounter.date_key == _today_key(), UsageCounter.bucket == bucket)
        .first()
    )
    return row.count if row else 0


def increment_usage(db: Session, user_id: str, bucket: str):
    today = _today_key()
    row = (
        db.query(UsageCounter)
        .filter(UsageCounter.user_id == user_id, UsageCounter.date_key == today, UsageCounter.bucket == bucket)
        .first()
    )
    if row:
        row.count += 1
    else:
        row = UsageCounter(user_id=user_id, date_key=today, bucket=bucket, count=1)
        db.add(row)
    db.commit()


def enforce_daily_limit(db: Session, user: User, bucket: str):
    """Raises HTTP 402 if the user has hit their plan's daily limit for this bucket."""
    limits = get_plan_limits(user)
    limit = limits.get(bucket)
    if limit is None:
        return
    used = get_today_count(db, user.id, bucket)
    if used >= limit:
        raise HTTPException(
            402,
            f"You've reached your {user.plan} plan's daily limit of {limit} for this feature. "
            f"Upgrade to Pro for a higher limit, or try again tomorrow.",
        )


def enforce_document_limit(db: Session, user: User):
    """Raises HTTP 402 if uploading another document would exceed the plan's document cap."""
    limits = get_plan_limits(user)
    max_docs = limits.get("documents")
    if max_docs is None:
        return
    current = db.query(Document).filter(Document.user_id == user.id).count()
    if current >= max_docs:
        raise HTTPException(
            402,
            f"Your {user.plan} plan allows up to {max_docs} documents. "
            f"Delete an existing one or upgrade to Pro.",
        )


def get_usage_summary(db: Session, user: User) -> dict:
    limits = get_plan_limits(user)
    doc_count = db.query(Document).filter(Document.user_id == user.id).count()
    return {
        "plan": user.plan,
        "documents": {"used": doc_count, "limit": limits["documents"]},
        "chat_today": {"used": get_today_count(db, user.id, "chat"), "limit": limits["chat"]},
        "agent_today": {"used": get_today_count(db, user.id, "agent"), "limit": limits["agent"]},
    }
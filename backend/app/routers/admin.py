"""
app/routers/admin.py
Admin-only endpoints: how many users, how much usage, which features are
popular. Gated by User.is_admin (see core/deps.get_current_admin_user).
Bootstrap your first admin via the ADMIN_USERNAMES env var (see auth.py).
"""

from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_admin_user
from app.models import AgentRun, ChatMessage, Document, User
from app.schemas import AdminStatsOut, AdminUserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
def list_users(_: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    out = []
    for u in users:
        doc_count = db.query(Document).filter(Document.user_id == u.id).count()
        out.append(AdminUserOut(
            id=u.id, username=u.username, email=u.email, plan=u.plan,
            is_admin=u.is_admin, email_verified=u.email_verified,
            document_count=doc_count, created_at=u.created_at.isoformat(),
        ))
    return out


@router.post("/users/{user_id}/promote")
def promote_user(user_id: str, _: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"message": "User not found."}
    user.is_admin = True
    db.commit()
    return {"message": f"{user.username} is now an admin."}


@router.post("/users/{user_id}/set-plan")
def set_user_plan(user_id: str, plan: str, _: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    if plan not in ("free", "pro"):
        return {"message": "Plan must be 'free' or 'pro'."}
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"message": "User not found."}
    user.plan = plan
    db.commit()
    return {"message": f"{user.username}'s plan set to {plan}."}


@router.get("/stats", response_model=AdminStatsOut)
def stats(_: User = Depends(get_current_admin_user), db: Session = Depends(get_db)):
    total_users = db.query(User).count()
    total_documents = db.query(Document).count()
    total_chat_messages = db.query(ChatMessage).count()
    total_agent_runs = db.query(AgentRun).count()

    users_by_plan = dict(Counter(u.plan for u in db.query(User.plan).all()))

    agent_types = [row[0] for row in db.query(AgentRun.agent_type).all()]
    agent_runs_by_type = dict(Counter(agent_types))

    chat_features = [row[0] for row in db.query(ChatMessage.feature).all()]
    feature_usage = dict(Counter(chat_features))

    signups_last_7_days = {}
    today = datetime.utcnow().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = (
            db.query(User)
            .filter(User.created_at >= datetime.combine(day, datetime.min.time()),
                    User.created_at < datetime.combine(day + timedelta(days=1), datetime.min.time()))
            .count()
        )
        signups_last_7_days[day.isoformat()] = count

    return AdminStatsOut(
        total_users=total_users,
        total_documents=total_documents,
        total_chat_messages=total_chat_messages,
        total_agent_runs=total_agent_runs,
        users_by_plan=users_by_plan,
        agent_runs_by_type=agent_runs_by_type,
        feature_usage=feature_usage,
        signups_last_7_days=signups_last_7_days,
    )

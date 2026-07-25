"""
app/routers/auth.py
Register / login / refresh / delete account / reset workspace.
Same identifier-can-be-username-or-email login UX as the original
auth_service.py, migrated to Postgres + JWT.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token,
)
from app.models import User, Document, ChatMessage, AgentRun, SmartMemoryEntry
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, UserOut,
    MessageResponse, RefreshRequest,
)
from app.services import vectorstore

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.username == payload.username, User.email == payload.email)
    ).first()
    if existing:
        field = "Username" if existing.username == payload.username else "Email"
        raise HTTPException(400, f"{field} is already taken.")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    return {"message": "Account created successfully. Please log in."}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()
    user = db.query(User).filter(
        or_(User.username == identifier, User.email == identifier.lower())
    ).first()

    invalid = HTTPException(401, "Invalid username or password.")

    if user is None:
        raise invalid

    # --- brute-force lockout check ---
    if user.locked_until and user.locked_until > datetime.utcnow():
        minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() / 60) + 1
        raise HTTPException(
            429, f"Too many failed attempts. Try again in {minutes_left} minute(s)."
        )

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(
                minutes=settings.LOGIN_LOCKOUT_MINUTES
            )
            user.failed_login_attempts = 0
        db.commit()
        raise invalid

    # successful login — reset lockout state
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Called by the frontend when the access token expires, using the
    longer-lived refresh token, so the user isn't logged out every hour."""
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise ValueError
    except Exception:
        raise HTTPException(401, "Refresh token invalid or expired. Please log in again.")

    user = db.query(User).filter(User.id == data["sub"]).first()
    if not user:
        raise HTTPException(401, "User not found.")

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    """JWTs are stateless, so there's nothing to invalidate server-side —
    this endpoint exists so the frontend has a clean call to make before
    clearing its stored tokens, and so logout events are auditable."""
    return {"message": "Logged out successfully."}


@router.delete("/account", response_model=MessageResponse)
def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes the account AND all owned data (documents, chat history) —
    cascade is set on the model relationships, so this is one clean delete.
    The vector store isn't covered by SQL cascade, so it's cleared explicitly."""
    vectorstore.delete_all_for_user(current_user.id)
    db.delete(current_user)
    db.commit()
    return {"message": "Account and all associated data deleted."}


@router.post("/reset-workspace", response_model=MessageResponse)
def reset_workspace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Clears the user's documents + chat history but keeps the account —
    a 'start fresh' button, distinct from deleting the account entirely."""
    vectorstore.delete_all_for_user(current_user.id)
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
    db.query(AgentRun).filter(AgentRun.user_id == current_user.id).delete()
    db.query(SmartMemoryEntry).filter(SmartMemoryEntry.user_id == current_user.id).delete()
    db.query(Document).filter(Document.user_id == current_user.id).delete()
    db.commit()
    return {"message": "Workspace reset. All documents, chat history, and agent runs cleared."}

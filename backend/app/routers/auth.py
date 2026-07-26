"""
app/routers/auth.py
Register / login / refresh / delete account / reset workspace, plus email
verification, password reset, and TOTP two-factor auth.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, create_pending_2fa_token, decode_token,
    generate_secure_token,
)
from app.models import User, Document, ChatMessage, AgentRun, SmartMemoryEntry
from app.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, LoginResultResponse, UserOut,
    MessageResponse, RefreshRequest, VerifyEmailRequest, ResendVerificationRequest,
    ForgotPasswordRequest, ResetPasswordRequest, Enable2FAResponse, Confirm2FARequest,
    Login2FARequest, Disable2FARequest,
)
from app.services import vectorstore, email_service, totp_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _maybe_promote_admin(user: User, db: Session):
    """Auto-promotes usernames listed in ADMIN_USERNAMES on first login —
    a simple bootstrap so you don't need direct DB access to create your
    first admin account."""
    if user.username in settings.ADMIN_USERNAMES and not user.is_admin:
        user.is_admin = True
        db.commit()


@router.post("/register", response_model=MessageResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.username == payload.username, User.email == payload.email)
    ).first()
    if existing:
        field = "Username" if existing.username == payload.username else "Email"
        raise HTTPException(400, f"{field} is already taken.")

    verification_token = generate_secure_token()
    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        email_verification_token=verification_token,
        email_verification_sent_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()

    try:
        email_service.send_verification_email(user.email, user.username, verification_token)
    except Exception:
        pass  # email delivery failure shouldn't block registration

    return {"message": "Account created successfully. Check your email to verify your account, then log in."}


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email_verification_token == payload.token).first()
    if not user:
        raise HTTPException(400, "Invalid or expired verification link.")
    user.email_verified = True
    user.email_verification_token = None
    db.commit()
    return {"message": "Email verified successfully."}


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    # Always return the same message whether or not the account exists —
    # otherwise this endpoint becomes a way to enumerate registered emails.
    generic = {"message": "If that email is registered and unverified, a new link has been sent."}
    if not user or user.email_verified:
        return generic
    token = generate_secure_token()
    user.email_verification_token = token
    user.email_verification_sent_at = datetime.utcnow()
    db.commit()
    try:
        email_service.send_verification_email(user.email, user.username, token)
    except Exception:
        pass
    return generic


@router.post("/login", response_model=LoginResultResponse)
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

    # successful password check — reset lockout state
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    _maybe_promote_admin(user, db)

    if user.totp_enabled:
        return LoginResultResponse(requires_2fa=True, pending_token=create_pending_2fa_token(user.id))

    return LoginResultResponse(
        requires_2fa=False,
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/login/2fa", response_model=TokenResponse)
def login_2fa(payload: Login2FARequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.pending_token)
        if data.get("type") != "pending_2fa":
            raise ValueError
    except Exception:
        raise HTTPException(401, "That login session expired. Please log in again.")

    user = db.query(User).filter(User.id == data["sub"]).first()
    if not user or not user.totp_enabled:
        raise HTTPException(401, "Invalid session.")

    if not totp_service.verify_code(user.totp_secret, payload.code):
        raise HTTPException(400, "Invalid 2FA code.")

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id),
        user=UserOut.model_validate(user),
    )


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    generic = {"message": "If that email is registered, a password reset link has been sent."}
    if not user:
        return generic
    token = generate_secure_token()
    user.password_reset_token = token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    try:
        email_service.send_password_reset_email(user.email, user.username, token)
    except Exception:
        pass
    return generic


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.password_reset_token == payload.token).first()
    if not user or not user.password_reset_expires or user.password_reset_expires < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired reset link. Request a new one.")
    user.password_hash = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    return {"message": "Password reset successfully. Please log in."}


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
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _maybe_promote_admin(current_user, db)
    return current_user


@router.post("/logout", response_model=MessageResponse)
def logout(current_user: User = Depends(get_current_user)):
    """JWTs are stateless, so there's nothing to invalidate server-side —
    this endpoint exists so the frontend has a clean call to make before
    clearing its stored tokens, and so logout events are auditable."""
    return {"message": "Logged out successfully."}


# ---------------- Two-factor authentication ----------------

@router.post("/2fa/enable", response_model=Enable2FAResponse)
def enable_2fa(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generates a new secret + QR code. 2FA isn't actually turned on until
    /2fa/confirm verifies the user has scanned it correctly."""
    secret = totp_service.generate_secret()
    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.commit()
    qr = totp_service.generate_qr_code_base64(secret, current_user.username)
    return Enable2FAResponse(secret=secret, qr_code_base64=qr)


@router.post("/2fa/confirm", response_model=MessageResponse)
def confirm_2fa(payload: Confirm2FARequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.totp_secret:
        raise HTTPException(400, "Call /auth/2fa/enable first.")
    if not totp_service.verify_code(current_user.totp_secret, payload.code):
        raise HTTPException(400, "Invalid code. Check your authenticator app and try again.")
    current_user.totp_enabled = True
    db.commit()
    return {"message": "Two-factor authentication enabled."}


@router.post("/2fa/disable", response_model=MessageResponse)
def disable_2fa(payload: Disable2FARequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.totp_enabled:
        raise HTTPException(400, "Two-factor authentication isn't enabled.")
    if not totp_service.verify_code(current_user.totp_secret, payload.code):
        raise HTTPException(400, "Invalid code.")
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()
    return {"message": "Two-factor authentication disabled."}


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
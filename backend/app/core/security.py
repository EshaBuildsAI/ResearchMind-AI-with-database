"""
core/security.py
Password hashing — identical bcrypt approach to the original auth_service.py,
just moved here. Plus JWT create/verify for stateless session auth
(React stores the token, sends it on every request via Authorization header).
"""

import secrets
from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "username": username, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_pending_2fa_token(user_id: str) -> str:
    """Short-lived (5 min) token issued after password check succeeds but
    before the TOTP code is verified — proves "I know the password" without
    granting a real session yet."""
    expire = datetime.utcnow() + timedelta(minutes=5)
    payload = {"sub": user_id, "exp": expire, "type": "pending_2fa"}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Raises JWTError if invalid/expired — caller (get_current_user) turns
    that into a 401."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def generate_secure_token() -> str:
    """Used for email verification and password reset links — long, random,
    URL-safe, unguessable."""
    return secrets.token_urlsafe(32)

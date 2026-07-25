"""
app/services/totp_service.py
Two-factor auth via TOTP (Time-based One-Time Password) — free, no SMS
provider needed. Works with any standard authenticator app (Google
Authenticator, Authy, 1Password, etc.).
"""

import base64
import io

import pyotp
import qrcode

from app.core.config import settings


def generate_secret() -> str:
    return pyotp.random_base32()


def get_provisioning_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=settings.TOTP_ISSUER)


def generate_qr_code_base64(secret: str, username: str) -> str:
    """Returns a base64-encoded PNG the frontend can render as <img src="data:image/png;base64,...">."""
    uri = get_provisioning_uri(secret, username)
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def verify_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # allow 1 step of clock drift (~30s)

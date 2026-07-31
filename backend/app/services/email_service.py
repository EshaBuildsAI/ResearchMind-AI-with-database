"""
app/services/email_service.py
Sends verification/reset emails via Resend's HTTP API (HTTPS, port 443) —
free tier: 3,000 emails/month. This is the PRIMARY method because SMTP
(port 587) is blocked outbound on Railway and many other hosting
platforms — HTTPS never is, since it's the same protocol normal web
traffic uses.

Falls back to plain SMTP (your own Gmail/Outlook "app password") if
RESEND_API_KEY isn't set, and finally to console-logging if neither is
configured — so local dev works with zero setup either way.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

from app.core.config import settings

logger = logging.getLogger("researchmind")


def _send_via_resend(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Returns True on success, False if Resend isn't configured or the call failed."""
    if not settings.RESEND_API_KEY:
        return False
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={
                "from": f"ResearchMind AI <{settings.RESEND_FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
                "text": text_body,
            },
            timeout=15,
        )
        if response.status_code >= 400:
            logger.error(f"Resend API error sending to {to_email!r}: {response.status_code} {response.text[:300]}")
            return False
        logger.info(f"Email sent via Resend to {to_email!r}: {subject!r}")
        return True
    except Exception as e:
        logger.error(f"Resend API request failed for {to_email!r}: {e}")
        return False


def _send_via_smtp(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Returns True on success, False if SMTP isn't configured or the call failed.
    Note: many hosting platforms (Railway included) block outbound SMTP —
    this fallback mainly helps for local development."""
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        logger.info(f"Email sent via SMTP to {to_email!r}: {subject!r}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email via SMTP to {to_email!r}: {e}")
        return False


def _send(to_email: str, subject: str, html_body: str, text_body: str):
    if _send_via_resend(to_email, subject, html_body, text_body):
        return
    if _send_via_smtp(to_email, subject, html_body, text_body):
        return
    logger.info(
        f"[email:console-fallback] Neither Resend nor SMTP configured — would have sent "
        f"to {to_email!r}, subject {subject!r}:\n{text_body}"
    )


def send_verification_email(to_email: str, username: str, token: str):
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your ResearchMind AI account"
    text = f"Hi {username},\n\nVerify your email by visiting:\n{link}\n\nIf you didn't create this account, ignore this email."
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2>Verify your email</h2>
      <p>Hi {username},</p>
      <p>Click the button below to verify your ResearchMind AI account:</p>
      <p><a href="{link}" style="background:#14b8a6;color:#070f0f;padding:10px 20px;
         border-radius:8px;text-decoration:none;font-weight:600;">Verify Email</a></p>
      <p style="color:#888;font-size:12px">Or paste this link: {link}</p>
    </div>"""
    _send(to_email, subject, html, text)


def send_password_reset_email(to_email: str, username: str, token: str):
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Reset your ResearchMind AI password"
    text = f"Hi {username},\n\nReset your password by visiting:\n{link}\n\nThis link expires in 1 hour. If you didn't request this, ignore this email."
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto">
      <h2>Reset your password</h2>
      <p>Hi {username},</p>
      <p>Click the button below to set a new password. This link expires in 1 hour.</p>
      <p><a href="{link}" style="background:#ff6f5e;color:#070f0f;padding:10px 20px;
         border-radius:8px;text-decoration:none;font-weight:600;">Reset Password</a></p>
      <p style="color:#888;font-size:12px">Or paste this link: {link}</p>
    </div>"""
    _send(to_email, subject, html, text)
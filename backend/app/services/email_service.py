"""
app/services/email_service.py
Sends verification/reset emails via plain SMTP — free, using your own
Gmail/Outlook/etc. account (an "app password", not your real password).
No paid email API (SendGrid/Mailgun/etc.) required.

If SMTP isn't configured (local dev), emails are logged to the console
instead of failing, so registration/reset flows still work without setup.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger("researchmind")


def _send(to_email: str, subject: str, html_body: str, text_body: str):
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        logger.info(
            f"[email:console-fallback] SMTP not configured — would have sent "
            f"to {to_email!r}, subject {subject!r}:\n{text_body}"
        )
        return

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
        logger.info(f"Email sent to {to_email!r}: {subject!r}")
    except Exception as e:
        # Don't crash the request just because email delivery failed —
        # log it and let the caller decide whether that's fatal.
        logger.error(f"Failed to send email to {to_email!r}: {e}")
        raise


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

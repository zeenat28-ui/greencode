"""Production Email Service for GreenCode Auditor.

Supports real-world transactional emails:
- Account Email Verification
- Password Reset Flow with expiring tokens
- Welcome notifications & SCI audit alerts

Configurable via SMTP (Gmail, SendGrid, Amazon SES, Mailgun, Brevo) or
zero-config Dev Console Mode (logs clickable token link to console when SMTP is unset).
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

logger = logging.getLogger("greencode.mailer")

SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.environ.get("SMTP_FROM", "no-reply@greencode.dev").strip()
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
APP_UI_URL = os.environ.get("APP_UI_URL", "http://localhost:8501").rstrip("/")


def is_smtp_configured() -> bool:
    """Check if real SMTP credentials are provided."""
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def dispatch_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Send transactional email via SMTP or fallback to Dev Console Mode."""
    clean_to = to_email.strip().lower()

    if not is_smtp_configured():
        # Dev Console Mode: Safe for local testing, CI/CD, and workstation development
        msg = f"[DEV EMAIL DISPATCH] To: {clean_to} | Subject: '{subject}'"
        print(f"\n{'='*60}\n{msg}\n{'-'*60}\n{text_content or html_content}\n{'='*60}\n")
        logger.info(msg)
        return {
            "success": True,
            "mode": "DEV_CONSOLE",
            "to": clean_to,
            "subject": subject,
            "message": "Email logged to console (configure SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env for live inbox delivery).",
        }

    # Live SMTP Dispatch
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = clean_to

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        server.ehlo()
        if SMTP_PORT in (587, 25):
            server.starttls()
            server.ehlo()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [clean_to], msg.as_string())
        server.quit()

        logger.info(f"Email successfully delivered to {clean_to} via {SMTP_HOST}")
        return {
            "success": True,
            "mode": "SMTP_LIVE",
            "to": clean_to,
            "subject": subject,
            "message": "Email sent to live inbox.",
        }
    except Exception as e:
        logger.error(f"Failed to deliver email to {clean_to}: {str(e)}")
        return {
            "success": False,
            "mode": "SMTP_ERROR",
            "error": str(e),
            "to": clean_to,
        }


def send_verification_email(to_email: str, username: str, verification_token: str) -> Dict[str, Any]:
    """Send account confirmation email with verification link."""
    verify_url = f"{APP_BASE_URL}/api/auth/verify-email?token={verification_token}"
    subject = "Verify your GreenCode Auditor account"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8faf6; color: #17290c; margin: 0; padding: 24px; }}
            .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border: 1px solid #d5e6cd; border-radius: 12px; padding: 32px; box-shadow: 0 4px 16px rgba(23,41,12,0.06); }}
            .logo {{ font-size: 1.4rem; font-weight: 800; color: #669933; margin-bottom: 20px; }}
            .btn {{ display: inline-block; background-color: #669933; color: #ffffff !important; font-weight: 700; text-decoration: none; padding: 12px 28px; border-radius: 6px; margin: 20px 0; font-size: 0.95rem; }}
            .footer {{ font-size: 0.78rem; color: #6b7280; margin-top: 24px; border-top: 1px solid #e5e7eb; padding-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo">🌿 GreenCode Auditor</div>
            <h2>Welcome to GreenCode, @{username}!</h2>
            <p>Thank you for registering. Please confirm your email address to activate your full developer profile and unlock high-throughput CI/CD scanning.</p>
            <div style="text-align: center;">
                <a href="{verify_url}" class="btn">Verify Email Address</a>
            </div>
            <p style="font-size: 0.85rem; color: #4b5563;">Or paste this link into your browser:<br>
            <a href="{verify_url}" style="color: #669933; word-break: break-all;">{verify_url}</a></p>
            <div class="footer">
                If you did not create a GreenCode Auditor account, you can safely ignore this email.
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
    Welcome to GreenCode Auditor, @{username}!

    Please confirm your email address by visiting this link:
    {verify_url}

    If you did not create an account, you can safely ignore this email.
    """
    return dispatch_email(to_email, subject, html, text)


def send_password_reset_email(to_email: str, username: str, reset_token: str) -> Dict[str, Any]:
    """Send password reset link with 1-hour expiration."""
    reset_url = f"{APP_UI_URL}/?reset_token={reset_token}"
    api_reset_url = f"{APP_BASE_URL}/api/auth/reset-password?token={reset_token}"
    subject = "Reset your GreenCode Auditor password"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8faf6; color: #17290c; margin: 0; padding: 24px; }}
            .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border: 1px solid #d5e6cd; border-radius: 12px; padding: 32px; box-shadow: 0 4px 16px rgba(23,41,12,0.06); }}
            .logo {{ font-size: 1.4rem; font-weight: 800; color: #669933; margin-bottom: 20px; }}
            .btn {{ display: inline-block; background-color: #243d15; color: #ffffff !important; font-weight: 700; text-decoration: none; padding: 12px 28px; border-radius: 6px; margin: 20px 0; font-size: 0.95rem; }}
            .footer {{ font-size: 0.78rem; color: #6b7280; margin-top: 24px; border-top: 1px solid #e5e7eb; padding-top: 16px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="logo">🌿 GreenCode Auditor</div>
            <h2>Password Reset Request</h2>
            <p>Hi @{username}, we received a request to reset the password for your GreenCode Auditor account.</p>
            <div style="text-align: center;">
                <a href="{reset_url}" class="btn">Reset My Password</a>
            </div>
            <p style="font-size: 0.85rem; color: #4b5563;">This security link is valid for <b>60 minutes</b>.<br>
            Direct Token Link: <a href="{reset_url}" style="color: #669933; word-break: break-all;">{reset_url}</a></p>
            <div class="footer">
                If you did not request a password reset, please ignore this email or check your account security.
            </div>
        </div>
    </body>
    </html>
    """

    text = f"""
    Password Reset Request for @{username}

    We received a request to reset your password. You can reset it using this link (valid for 60 minutes):
    {reset_url}

    Security token: {reset_token}

    If you did not request this, you can safely ignore this email.
    """
    return dispatch_email(to_email, subject, html, text)


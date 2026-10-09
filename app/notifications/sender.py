"""Notification Senders (Slack, Microsoft Teams, Email, Generic Webhook)."""

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, Optional
from app.mailer import dispatch_email

logger = logging.getLogger("greencode.notifications")


class NotificationSender:
    """Dispatches notifications across enterprise communication backplanes."""

    @classmethod
    def send_webhook(cls, webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch JSON webhook to Slack, MS Teams, or generic webhook receiver."""
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "GreenCode-Sentinel/2.4"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                status_code = resp.status
                return {"success": status_code in (200, 201, 204), "status_code": status_code}
        except Exception as e:
            logger.warning(f"Webhook dispatch failed: {str(e)}")
            return {"success": False, "error": str(e)}

    @classmethod
    def send_slack(cls, webhook_url: str, title: str, text: str, severity: str = "INFO") -> Dict[str, Any]:
        color = "#10b981" if severity == "INFO" else ("#f59e0b" if severity == "WARNING" else "#ef4444")
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"🌿 GreenCode: {title}",
                    "text": text,
                    "footer": f"Severity: {severity}",
                }
            ]
        }
        return cls.send_webhook(webhook_url, payload)

    @classmethod
    def send_email(cls, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        html = f"<div style='font-family:sans-serif;'><h3>{subject}</h3><p>{body}</p></div>"
        return dispatch_email(to_email=to_email, subject=subject, html_content=html, text_content=body)


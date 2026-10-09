"""Enterprise Notification Routing Service."""

import logging
from typing import Any, Dict, Optional
from app.notifications.sender import NotificationSender

logger = logging.getLogger("greencode.notifications.service")


class NotificationService:
    """Routes alerts to appropriate notification channels."""

    @classmethod
    def dispatch_alert(
        cls,
        title: str,
        message: str,
        severity: str = "INFO",
        channel: str = "console",
        webhook_url: Optional[str] = None,
        recipient_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Notification [{severity}] via {channel}: {title}")

        if channel == "slack" and webhook_url:
            return NotificationSender.send_slack(webhook_url, title, message, severity)
        elif channel == "webhook" and webhook_url:
            return NotificationSender.send_webhook(webhook_url, {"title": title, "message": message, "severity": severity})
        elif channel == "email" and recipient_email:
            return NotificationSender.send_email(recipient_email, title, message)

        # Default console delivery
        return {
            "success": True,
            "channel": "console",
            "title": title,
            "severity": severity,
            "status": "DELIVERED_TO_CONSOLE",
        }


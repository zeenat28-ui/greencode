"""Enterprise Notifications API Router."""

from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status
from app.notifications.models import NotificationPayload
from app.notifications.service import NotificationService

router = APIRouter(prefix="/api/notifications", tags=["Enterprise Alerts & Notifications"])


@router.post("/send")
async def send_notification(payload: NotificationPayload):
    """Dispatch an alert message across configured channels."""
    return NotificationService.dispatch_alert(
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        channel=payload.channel,
        webhook_url=payload.webhook_url,
        recipient_email=payload.recipient_email,
    )


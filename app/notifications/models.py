"""Enterprise Notification Models."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


@dataclass
class Alert:
    title: str
    message: str
    severity: str  # INFO, WARNING, CRITICAL, BREACH
    source: str
    metadata: Optional[Dict[str, Any]] = None


class NotificationPayload(BaseModel):
    title: str = Field(..., min_length=2)
    message: str = Field(..., min_length=2)
    severity: str = Field("INFO", pattern="^(INFO|WARNING|CRITICAL|BREACH)$")
    channel: str = Field("console", pattern="^(console|slack|teams|email|webhook)$")
    webhook_url: Optional[str] = None
    recipient_email: Optional[str] = None


__all__ = [
    "Alert",
    "NotificationPayload",
]


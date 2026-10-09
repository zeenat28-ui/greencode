"""Enterprise Admin Models."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


@dataclass
class SystemHealth:
    status: str
    database: str
    version: str
    environment: str
    uptime_seconds: float


class UpdateSettingsRequest(BaseModel):
    enforce_policies: Optional[bool] = None
    enable_k8s_rollback: Optional[bool] = None
    default_monthly_budget_kg: Optional[float] = None
    alert_channel: Optional[str] = None


__all__ = [
    "SystemHealth",
    "UpdateSettingsRequest",
]


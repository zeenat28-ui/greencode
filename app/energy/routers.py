"""Enterprise Energy & Carbon API Router.

SECURITY
--------
Both routes require a valid Bearer access token.  The team budget route is
organisation-scoped, so the tenant boundary is enforced: the caller's tenant
comes from the VERIFIED token, and a path ``org_id`` naming another tenant is
rejected with 403 unless the caller is a platform ``superadmin``.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.energy.monitor import EnergyMonitor
from app.services.budget_service import BudgetNotConfiguredError, BudgetService
from app.auth.dependencies import enforce_tenant_scope, require_permission
from app.auth.roles import Permission

router = APIRouter(prefix="/api/energy", tags=["Energy Telemetry & Budgets"])


class CalculateEnergyRequest(BaseModel):
    duration_seconds: float = Field(..., gt=0)
    cpu_utilization_pct: float = Field(..., ge=0, le=100)
    memory_mb: float = Field(256.0, gt=0)
    cloud_instance: str = "generic_container"
    raw_hardware_joules: Optional[float] = None


@router.post("/calculate")
async def calculate_energy(
    payload: CalculateEnergyRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.READ_METRICS)),
):
    """Derive defensible energy consumption and carbon cost using SPECpower calibrated curves."""
    try:
        reading = EnergyMonitor.measure(
            duration_seconds=payload.duration_seconds,
            cpu_utilization_pct=payload.cpu_utilization_pct,
            memory_mb=payload.memory_mb,
            cloud_instance=payload.cloud_instance,
            is_hardware_counter_available=payload.raw_hardware_joules is not None,
            raw_hardware_joules=payload.raw_hardware_joules,
        )
        return reading
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budgets/team/{org_id}/{team_id}")
async def get_team_budget_status(
    org_id: int,
    team_id: str,
    period: Optional[str] = None,
    actor: Dict[str, Any] = Depends(require_permission(Permission.READ_METRICS)),
):
    """Retrieve team carbon quota consumption, burn rate, and alerts."""
    enforce_tenant_scope(actor, int(org_id))
    try:
        return BudgetService.get_team_status(org_id=org_id, team_id=team_id, period=period)
    except BudgetNotConfiguredError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

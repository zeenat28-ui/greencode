"""Enterprise Energy & Carbon API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.energy.monitor import EnergyMonitor
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/api/energy", tags=["Energy Telemetry & Budgets"])


class CalculateEnergyRequest(BaseModel):
    duration_seconds: float = Field(..., gt=0)
    cpu_utilization_pct: float = Field(..., ge=0, le=100)
    memory_mb: float = Field(256.0, gt=0)
    cloud_instance: str = "generic_container"
    raw_hardware_joules: Optional[float] = None


@router.post("/calculate")
async def calculate_energy(payload: CalculateEnergyRequest):
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
async def get_team_budget_status(org_id: int, team_id: str, period: Optional[str] = None):
    """Retrieve team carbon quota consumption, burn rate, and alerts."""
    return BudgetService.get_team_status(org_id=org_id, team_id=team_id, period=period)


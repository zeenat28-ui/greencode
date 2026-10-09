"""Enterprise Policy Models."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.database import EnergyPolicy


class EnergyPolicyPayload(BaseModel):
    name: Optional[str] = "Default Policy"
    max_regression_pct: float = Field(25.0, ge=0.0, le=500.0)
    max_energy_per_run_joules: float = Field(1.0, ge=0.0)
    max_sci_score: float = Field(80.0, ge=0.0, le=100.0)
    warning_threshold_pct: float = Field(70.0, ge=0.0, le=100.0)
    critical_threshold_pct: float = Field(90.0, ge=0.0, le=100.0)
    breach_threshold_pct: float = Field(100.0, ge=0.0, le=200.0)
    auto_block_deploy: bool = True
    auto_rollback_k8s: bool = True
    dirty_grid_threshold_gco2e: float = Field(450.0, ge=0.0)


class PolicyEvaluationRequest(BaseModel):
    org_id: int
    current_energy: float = Field(..., ge=0.0)
    baseline_energy: float = Field(..., ge=0.0)
    team_budget_consumed: float = 0.0
    team_budget_total: float = 500.0
    grid_intensity: float = 380.0
    project_id: Optional[int] = None


__all__ = [
    "EnergyPolicy",
    "EnergyPolicyPayload",
    "PolicyEvaluationRequest",
]


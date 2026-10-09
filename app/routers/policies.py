"""Enterprise Energy Policy REST API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.policy_service import PolicyService

router = APIRouter(prefix="/api/policies", tags=["Energy Policies & Guardrails"])


class PolicySaveRequest(BaseModel):
    org_id: int = 1
    project_id: Optional[int] = None
    name: str = "Enterprise Standard Policy"
    max_regression_pct: float = Field(25.0, ge=0.0)
    max_energy_per_run_joules: float = Field(1.0, gt=0.0)
    max_sci_score: float = Field(80.0, gt=0.0)
    warning_threshold_pct: float = Field(70.0, ge=0.0)
    critical_threshold_pct: float = Field(90.0, ge=0.0)
    breach_threshold_pct: float = Field(100.0, ge=0.0)
    auto_block_deploy: bool = True
    auto_rollback_k8s: bool = True
    dirty_grid_threshold_gco2e: float = Field(450.0, gt=0.0)


class EvaluateRulesRequest(BaseModel):
    org_id: int = 1
    current_energy: float = Field(..., ge=0.0)
    baseline_energy: float = Field(..., gt=0.0)
    team_budget_consumed: float = 0.0
    team_budget_total: float = 500.0
    grid_intensity: float = 380.0
    project_id: Optional[int] = None


@router.get("/{org_id}")
async def get_enterprise_policy(org_id: int, project_id: Optional[int] = Query(None)):
    """Fetch active energy guardrail policies for an enterprise organization or project."""
    return PolicyService.get_policy(org_id=org_id, project_id=project_id)


@router.post("", status_code=status.HTTP_200_OK)
async def save_enterprise_policy(payload: PolicySaveRequest):
    """Save or update organizational energy policies and threshold rules."""
    return PolicyService.save_policy(
        org_id=payload.org_id,
        policy_data=payload.model_dump(),
        project_id=payload.project_id,
    )


@router.post("/evaluate")
async def evaluate_deployment_rules(payload: EvaluateRulesRequest):
    """Evaluate live candidate metrics against organizational energy rules to determine gate verdict."""
    return PolicyService.evaluate_deployment_rules(
        org_id=payload.org_id,
        current_energy=payload.current_energy,
        baseline_energy=payload.baseline_energy,
        team_budget_consumed=payload.team_budget_consumed,
        team_budget_total=payload.team_budget_total,
        grid_intensity=payload.grid_intensity,
        project_id=payload.project_id,
    )


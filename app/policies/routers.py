"""Enterprise Policy API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.policies.service import PolicyService
from app.auth.dependencies import get_current_actor, get_tenant_actor, require_permission
from app.auth.roles import Permission, Role, normalize_role

router = APIRouter(prefix="/api/policies", tags=["Energy Policies & Guardrails"])


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
    org_id: int = 1
    current_energy: float = Field(..., ge=0.0)
    baseline_energy: float = Field(..., ge=0.0)
    team_budget_consumed: float = 0.0
    team_budget_total: float = 500.0
    grid_intensity: float = 380.0
    project_id: Optional[int] = None


@router.get("/{org_id}")
async def get_policy(
    org_id: int,
    project_id: Optional[int] = Query(None),
    actor: Dict[str, Any] = Depends(get_tenant_actor),
):
    """Fetch active policy for organization or specific project."""
    return PolicyService.get_policy(org_id=org_id, project_id=project_id)


@router.post("/{org_id}")
async def save_policy(
    org_id: int,
    payload: EnergyPolicyPayload,
    project_id: Optional[int] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.OVERRIDE_POLICIES)),
    tenant: Dict[str, Any] = Depends(get_tenant_actor),
):
    """Save or update organization energy policy."""
    return PolicyService.save_policy(
        org_id=org_id,
        policy_data=payload.model_dump(),
        project_id=project_id,
    )


@router.post("/evaluate")
async def evaluate_deployment(
    payload: PolicyEvaluationRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Evaluate deployment energy regression and team budget against rules."""
    # Tenant boundary: org_id is supplied in the body, so enforce it manually
    # against the verified token (superadmin may evaluate across tenants).
    role = normalize_role(actor.get("role"))
    if role != Role.SUPERADMIN and actor.get("org_id") != payload.org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Tenant isolation violation: token belongs to organization "
                f"{actor.get('org_id')} but requested organization {payload.org_id}"
            ),
        )
    return PolicyService.evaluate_deployment_rules(
        org_id=payload.org_id,
        current_energy=payload.current_energy,
        baseline_energy=payload.baseline_energy,
        team_budget_consumed=payload.team_budget_consumed,
        team_budget_total=payload.team_budget_total,
        grid_intensity=payload.grid_intensity,
        project_id=payload.project_id,
    )


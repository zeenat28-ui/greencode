"""Production Deployment, Energy Policies & Kubernetes Rollback Router."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.energy_policy_service import EnergyPolicyService
from app.services.rollback_service import RollbackService
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/api/energy", tags=["Production Deployment & Energy Policy"])


class PolicyUpdateRequest(BaseModel):
    project_id: int
    policy: Dict[str, Any]
    org_id: Optional[int] = 1


class CompareBaselineRequest(BaseModel):
    project_id: int
    current_metrics: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    grid_intensity: float = 380.0


class RollbackExecutionRequest(BaseModel):
    namespace: str = Field(..., min_length=1)
    deployment_name: str = Field(..., min_length=1)
    current_power_w: float = Field(..., ge=0.0)
    baseline_power_w: float = Field(..., ge=0.0)
    auto_trigger: bool = True
    org_id: Optional[int] = 1
    actor: str = "greencode-sentinel"


@router.post("/policy")
async def set_energy_policy(payload: PolicyUpdateRequest):
    """Define or update operational energy & carbon policies for a project."""
    return EnergyPolicyService.set_policy(
        project_id=payload.project_id,
        policy=payload.policy,
        org_id=payload.org_id,
    )


@router.post("/compare-baseline")
async def compare_against_baseline(payload: CompareBaselineRequest):
    """Compare canary deployment metrics against production baseline."""
    return EnergyPolicyService.evaluate_deployment_gate(
        project_id=payload.project_id,
        current_metrics=payload.current_metrics,
        baseline_metrics=payload.baseline_metrics,
        grid_intensity=payload.grid_intensity,
    )


@router.post("/rollback")
async def trigger_rollback(payload: RollbackExecutionRequest):
    """Evaluate power spike and execute automated/manual Kubernetes rollback."""
    return RollbackService.evaluate_and_rollback(
        namespace=payload.namespace,
        deployment_name=payload.deployment_name,
        current_power_w=payload.current_power_w,
        baseline_power_w=payload.baseline_power_w,
        org_id=payload.org_id,
        auto_trigger=payload.auto_trigger,
        actor=payload.actor,
    )


@router.get("/budgets")
async def get_energy_budgets(
    org_id: int = Query(1),
    team_id: str = Query("core-infra"),
    period: Optional[str] = Query(None),
):
    """Query active organizational energy & carbon budget statuses."""
    return BudgetService.get_team_status(
        org_id=org_id,
        team_id=team_id,
        period=period,
    )


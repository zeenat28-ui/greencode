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


class RegisterBaselineRequest(BaseModel):
    namespace: str = Field("host-runtime", min_length=1)
    deployment_name: str = Field(..., min_length=1)
    baseline_power_w: float = Field(..., gt=0.0)


class OpenAllocateBudgetRequest(BaseModel):
    org_id: int = 1
    team_id: str = Field(..., min_length=2)
    monthly_budget_kg: float = Field(..., gt=0.0)
    period: Optional[str] = None


class OpenEvaluatePRBudgetRequest(BaseModel):
    org_id: int = 1
    team_id: str = Field(..., min_length=2)
    additional_projected_kg_co2e: float = Field(..., ge=0.0)
    period: Optional[str] = None


@router.get("/workloads")
async def get_live_workloads(
    grid_intensity: float = Query(380.0, ge=0.0, le=2000.0),
    limit: int = Query(10, ge=1, le=50),
):
    """Discover and profile live workloads across CNCF Kepler, Docker Engine, or Host OS processes."""
    from app.kubernetes_profiler import kubernetes_monitor

    return kubernetes_monitor.list_live_workloads(
        grid_carbon_intensity=grid_intensity,
        max_workloads=limit,
    )


@router.post("/workloads/baseline")
async def set_workload_baseline(payload: RegisterBaselineRequest):
    """Register or update the certified power baseline (Watts) for a workload or deployment."""
    from app.kubernetes_profiler import kubernetes_monitor

    kubernetes_monitor.record_baseline(
        namespace=payload.namespace,
        deployment_name=payload.deployment_name,
        baseline_watts=payload.baseline_power_w,
    )
    return {
        "success": True,
        "namespace": payload.namespace,
        "deployment_name": payload.deployment_name,
        "baseline_power_w": payload.baseline_power_w,
    }


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
    team_status = BudgetService.get_team_status(
        org_id=org_id,
        team_id=team_id,
        period=period,
    )
    all_budgets = BudgetService.list_org_budgets(org_id=org_id, period=period)
    return {
        **team_status,
        "budgets": all_budgets,
    }


@router.post("/budgets/allocate")
async def allocate_energy_budget(payload: OpenAllocateBudgetRequest):
    """Allocate or update monthly carbon budget for a team and return refreshed budget list."""
    allocated = BudgetService.allocate_budget(
        org_id=payload.org_id,
        team_id=payload.team_id,
        monthly_budget_kg=payload.monthly_budget_kg,
        period=payload.period,
    )
    all_budgets = BudgetService.list_org_budgets(org_id=payload.org_id, period=payload.period)
    return {
        "success": True,
        "allocated": allocated,
        "budgets": all_budgets,
    }


@router.post("/budgets/evaluate-pr")
async def evaluate_pr_budget_gate(payload: OpenEvaluatePRBudgetRequest):
    """Evaluate whether an incoming pull request exceeds a team's monthly carbon quota."""
    return BudgetService.evaluate_pr_impact(
        org_id=payload.org_id,
        team_id=payload.team_id,
        additional_projected_kg_co2e=payload.additional_projected_kg_co2e,
        period=payload.period,
    )



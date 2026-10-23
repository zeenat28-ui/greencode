"""Production Deployment, Energy Policies & Kubernetes Rollback Router.

SECURITY
--------
Every route on this router requires a valid Bearer access token.  The
organisation-scoped routes additionally enforce the tenant boundary: the
caller's tenant always comes from the VERIFIED token, never from the
client-supplied ``org_id``.  Permissions mirror the canonical RBAC matrix in
``app.auth.roles`` and the protected counterparts of these routes:

======================================  =====================  ==============
Route                                   Permission             Tenant scope
======================================  =====================  ==============
``GET  /api/energy/workloads``          ``metrics:read``       n/a
``POST /api/energy/workloads/baseline`` ``deploy:approve``     n/a
``POST /api/energy/policy``             ``policy:override``    ``org_id``
``POST /api/energy/compare-baseline``   ``metrics:read``       project org
``POST /api/energy/rollback``           ``deploy:rollback``    ``org_id``
``GET  /api/energy/budgets``            ``metrics:read``       ``org_id``
``POST /api/energy/budgets/allocate``   ``budget:configure``   ``org_id``
``POST /api/energy/budgets/evaluate-pr`` authenticated         ``org_id``
======================================  =====================  ==============
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.energy_policy_service import EnergyPolicyService
from app.services.rollback_service import RollbackService
from app.services.budget_service import BudgetNotConfiguredError, BudgetService
from app.auth.dependencies import (
    enforce_tenant_scope,
    get_current_actor,
    require_permission,
)
from app.auth.roles import Permission

router = APIRouter(prefix="/api/energy", tags=["Production Deployment & Energy Policy"])


def _resolve_org_id(actor: Dict[str, Any], requested: Optional[int]) -> int:
    """Resolve the effective organisation id for the current request.

    A superadmin may target any organisation.  For every other role the
    organisation is ALWAYS the one embedded in the verified token; a
    client-supplied ``org_id`` naming another tenant is rejected with 403.
    """
    if requested is None:
        return int(actor.get("org_id") or 1)
    enforce_tenant_scope(actor, int(requested))
    return int(requested)


def _enforce_project_scope(
    actor: Dict[str, Any],
    project_id: int,
    requested: Optional[int] = None,
) -> int:
    """Resolve and authorise the organisation that owns ``project_id``.

    The authoritative organisation is the one stored on the project row - a
    client-supplied ``org_id`` is never trusted to widen access.  When the
    project is unknown (it does not exist yet) the tenant is resolved from the
    verified token, and an explicit cross-tenant ``org_id`` is rejected.
    """
    project_org_id = EnergyPolicyService.get_project_org_id(project_id)
    if project_org_id is not None:
        enforce_tenant_scope(actor, project_org_id, resource=f"project {project_id}")
        return project_org_id
    return _resolve_org_id(actor, requested)


class PolicyUpdateRequest(BaseModel):
    project_id: int
    policy: Dict[str, Any]
    org_id: Optional[int] = None


class CompareBaselineRequest(BaseModel):
    project_id: int
    current_metrics: Dict[str, Any]
    baseline_metrics: Dict[str, Any]
    grid_intensity: float = 380.0
    org_id: Optional[int] = None


class RollbackExecutionRequest(BaseModel):
    namespace: str = Field(..., min_length=1)
    deployment_name: str = Field(..., min_length=1)
    current_power_w: float = Field(..., ge=0.0)
    baseline_power_w: float = Field(..., ge=0.0)
    auto_trigger: bool = True
    org_id: Optional[int] = None
    actor: str = "greencode-sentinel"


class RegisterBaselineRequest(BaseModel):
    namespace: str = Field("host-runtime", min_length=1)
    deployment_name: str = Field(..., min_length=1)
    baseline_power_w: float = Field(..., gt=0.0)


class OpenAllocateBudgetRequest(BaseModel):
    org_id: Optional[int] = None
    team_id: str = Field(..., min_length=2)
    monthly_budget_kg: float = Field(..., gt=0.0)
    period: Optional[str] = None


class OpenEvaluatePRBudgetRequest(BaseModel):
    org_id: Optional[int] = None
    team_id: str = Field(..., min_length=2)
    additional_projected_kg_co2e: float = Field(..., ge=0.0)
    period: Optional[str] = None


@router.get("/workloads")
async def get_live_workloads(
    grid_intensity: float = Query(380.0, ge=0.0, le=2000.0),
    limit: int = Query(10, ge=1, le=50),
    actor: Dict[str, Any] = Depends(require_permission(Permission.READ_METRICS)),
):
    """Discover and profile live workloads across CNCF Kepler, Docker Engine, or Host OS processes."""
    from app.kubernetes_profiler import kubernetes_monitor

    return kubernetes_monitor.list_live_workloads(
        grid_carbon_intensity=grid_intensity,
        max_workloads=limit,
    )


@router.post("/workloads/baseline")
async def set_workload_baseline(
    payload: RegisterBaselineRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.APPROVE_DEPLOY)),
):
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
async def set_energy_policy(
    payload: PolicyUpdateRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.OVERRIDE_POLICIES)),
):
    """Define or update operational energy & carbon policies for a project."""
    org_id = _enforce_project_scope(actor, payload.project_id, payload.org_id)
    return EnergyPolicyService.set_policy(
        project_id=payload.project_id,
        policy=payload.policy,
        org_id=org_id,
    )


@router.post("/compare-baseline")
async def compare_against_baseline(
    payload: CompareBaselineRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.READ_METRICS)),
):
    """Compare canary deployment metrics against production baseline."""
    _enforce_project_scope(actor, payload.project_id, payload.org_id)
    return EnergyPolicyService.evaluate_deployment_gate(
        project_id=payload.project_id,
        current_metrics=payload.current_metrics,
        baseline_metrics=payload.baseline_metrics,
        grid_intensity=payload.grid_intensity,
    )


@router.post("/rollback")
async def trigger_rollback(
    payload: RollbackExecutionRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXECUTE_ROLLBACK)),
):
    """Evaluate power spike and execute automated/manual Kubernetes rollback.

    This is a potentially destructive action, so it requires the explicit
    ``deploy:rollback`` permission and the tenant boundary is enforced
    against the requested organization.
    """
    org_id = _resolve_org_id(actor, payload.org_id)
    return RollbackService.evaluate_and_rollback(
        namespace=payload.namespace,
        deployment_name=payload.deployment_name,
        current_power_w=payload.current_power_w,
        baseline_power_w=payload.baseline_power_w,
        org_id=org_id,
        auto_trigger=payload.auto_trigger,
        actor=actor.get("username") or payload.actor,
    )


@router.get("/budgets")
async def get_energy_budgets(
    org_id: Optional[int] = Query(None),
    team_id: str = Query("core-infra"),
    period: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.READ_METRICS)),
):
    """Query active organizational energy & carbon budget statuses."""
    effective_org_id = _resolve_org_id(actor, org_id)
    all_budgets = BudgetService.list_org_budgets(org_id=effective_org_id, period=period)
    team_status = next((budget for budget in all_budgets if budget["team_id"] == team_id), None)
    return {
        "org_id": effective_org_id,
        "team_id": team_id,
        "period": period,
        **(team_status or {}),
        "team_status": team_status,
        "budgets": all_budgets,
    }


@router.post("/budgets/allocate")
async def allocate_energy_budget(
    payload: OpenAllocateBudgetRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.CONFIGURE_BUDGET)),
):
    """Allocate or update monthly carbon budget for a team and return refreshed budget list."""
    org_id = _resolve_org_id(actor, payload.org_id)
    allocated = BudgetService.allocate_budget(
        org_id=org_id,
        team_id=payload.team_id,
        monthly_budget_kg=payload.monthly_budget_kg,
        period=payload.period,
    )
    all_budgets = BudgetService.list_org_budgets(org_id=org_id, period=payload.period)
    return {
        "success": True,
        "allocated": allocated,
        "budgets": all_budgets,
    }


@router.post("/budgets/evaluate-pr")
async def evaluate_pr_budget_gate(
    payload: OpenEvaluatePRBudgetRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Evaluate whether an incoming pull request exceeds a team's monthly carbon quota."""
    org_id = _resolve_org_id(actor, payload.org_id)
    try:
        return BudgetService.evaluate_pr_impact(
            org_id=org_id,
            team_id=payload.team_id,
            additional_projected_kg_co2e=payload.additional_projected_kg_co2e,
            period=payload.period,
        )
    except BudgetNotConfiguredError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

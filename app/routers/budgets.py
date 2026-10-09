"""Team & Service Carbon Budget Management and PR Gate API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.budget_service import BudgetService
from app.auth.dependencies import get_current_actor, require_permission
from app.auth.roles import Permission, Role, normalize_role

router = APIRouter(prefix="/api/budgets", tags=["Carbon Budgets & Quotas"])


def _enforce_tenant(actor: Dict[str, Any], org_id: int) -> None:
    """Refuse cross-tenant access unless the caller is a platform superadmin."""
    role = normalize_role(actor.get("role"))
    if role != Role.SUPERADMIN and actor.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Tenant isolation violation: token belongs to organization "
                f"{actor.get('org_id')} but requested organization {org_id}"
            ),
        )


class AllocateBudgetRequest(BaseModel):
    org_id: int = 1
    team_id: str = Field(..., min_length=2)
    monthly_budget_kg: float = Field(..., gt=0.0)
    period: Optional[str] = None


class ConsumeEmissionRequest(BaseModel):
    org_id: int = 1
    team_id: str = Field(..., min_length=2)
    consumed_kg: float = Field(..., ge=0.0)
    period: Optional[str] = None


class EvaluatePREmissionRequest(BaseModel):
    org_id: int = 1
    team_id: str = Field(..., min_length=2)
    additional_projected_kg_co2e: float = Field(..., ge=0.0)
    period: Optional[str] = None


@router.post("/allocate", status_code=status.HTTP_200_OK)
async def allocate_team_budget(
    payload: AllocateBudgetRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.CONFIGURE_BUDGET)),
):
    """Allocate or adjust monthly carbon budget for a team or service."""
    _enforce_tenant(actor, payload.org_id)
    return BudgetService.allocate_budget(
        org_id=payload.org_id,
        team_id=payload.team_id,
        monthly_budget_kg=payload.monthly_budget_kg,
        period=payload.period,
    )


@router.get("/status/{team_id}")
async def get_team_budget_status(
    team_id: str,
    org_id: int = Query(1),
    period: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Fetch current consumption, burn rate, and alert level for a team."""
    _enforce_tenant(actor, org_id)
    return BudgetService.get_team_status(
        org_id=org_id,
        team_id=team_id,
        period=period,
    )


@router.post("/consume")
async def record_team_consumption(
    payload: ConsumeEmissionRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Record incremental emissions and update budget consumption status."""
    _enforce_tenant(actor, payload.org_id)
    return BudgetService.record_emission(
        org_id=payload.org_id,
        team_id=payload.team_id,
        consumed_kg=payload.consumed_kg,
        period=payload.period,
    )


@router.post("/evaluate-pr")
async def evaluate_pr_carbon_impact(
    payload: EvaluatePREmissionRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Evaluate whether an incoming pull request exceeds monthly team carbon budget."""
    _enforce_tenant(actor, payload.org_id)
    return BudgetService.evaluate_pr_impact(
        org_id=payload.org_id,
        team_id=payload.team_id,
        additional_projected_kg_co2e=payload.additional_projected_kg_co2e,
        period=payload.period,
    )


"""Team & Service Carbon Budget Management and PR Gate API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.budget_service import BudgetService

router = APIRouter(prefix="/api/budgets", tags=["Carbon Budgets & Quotas"])


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
async def allocate_team_budget(payload: AllocateBudgetRequest):
    """Allocate or adjust monthly carbon budget for a team or service."""
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
):
    """Fetch current consumption, burn rate, and alert level for a team."""
    return BudgetService.get_team_status(
        org_id=org_id,
        team_id=team_id,
        period=period,
    )


@router.post("/consume")
async def record_team_consumption(payload: ConsumeEmissionRequest):
    """Record incremental emissions and update budget consumption status."""
    return BudgetService.record_emission(
        org_id=payload.org_id,
        team_id=payload.team_id,
        consumed_kg=payload.consumed_kg,
        period=payload.period,
    )


@router.post("/evaluate-pr")
async def evaluate_pr_carbon_impact(payload: EvaluatePREmissionRequest):
    """Evaluate whether an incoming pull request exceeds monthly team carbon budget."""
    return BudgetService.evaluate_pr_impact(
        org_id=payload.org_id,
        team_id=payload.team_id,
        additional_projected_kg_co2e=payload.additional_projected_kg_co2e,
        period=payload.period,
    )


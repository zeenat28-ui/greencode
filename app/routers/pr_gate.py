"""Pre-Deploy PR Energy Delta Gate REST API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.services.energy_diff_service import EnergyDiffService

router = APIRouter(prefix="/api/pr-gate", tags=["CI/CD Pre-Deploy PR Gate"])


class PREvaluationRequest(BaseModel):
    base_scan: Dict[str, Any]
    head_scan: Dict[str, Any]
    monthly_invocations: int = Field(10_000_000, gt=0)
    grid_zone: str = "US-CAL-CISO"
    instance_type: str = "c6g.xlarge"
    max_regression_pct: float = Field(15.0, ge=0.0)


@router.post("/evaluate", status_code=status.HTTP_200_OK)
async def evaluate_pr_energy_gate(payload: PREvaluationRequest):
    """Evaluate base vs head code analysis to generate gate decision and PR comment."""
    return EnergyDiffService.compare_scans(
        base_scan=payload.base_scan,
        head_scan=payload.head_scan,
        monthly_invocations=payload.monthly_invocations,
        grid_zone=payload.grid_zone,
        instance_type=payload.instance_type,
        max_regression_pct=payload.max_regression_pct,
    )


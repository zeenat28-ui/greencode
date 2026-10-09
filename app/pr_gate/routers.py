"""Enterprise Pull Request Energy Gate API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.pr_gate.diff_analyzer import EnergyDiffService

router = APIRouter(prefix="/api/pr-gate", tags=["PR Energy Delta Gate"])


class PRComparePayload(BaseModel):
    base_scan: Dict[str, Any]
    head_scan: Dict[str, Any]
    monthly_invocations: int = Field(10_000_000, gt=0)
    grid_zone: str = "US-CAL-CISO"
    instance_type: str = "c6g.xlarge"
    max_regression_pct: float = Field(15.0, ge=0.0)


@router.post("/compare")
@router.post("/evaluate")
async def compare_pr_energy(payload: PRComparePayload):
    """Calculate pre-deployment energy delta, annual USD delta, and sticky comment markdown."""
    return EnergyDiffService.compare_scans(
        base_scan=payload.base_scan,
        head_scan=payload.head_scan,
        monthly_invocations=payload.monthly_invocations,
        grid_zone=payload.grid_zone,
        instance_type=payload.instance_type,
        max_regression_pct=payload.max_regression_pct,
    )


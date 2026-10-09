"""Enterprise Kubernetes Telemetry & Rollback API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.kubernetes.models import RollbackEvaluationRequest
from app.kubernetes.service import RollbackService

router = APIRouter(prefix="/api/kubernetes", tags=["Kubernetes & Automated Rollbacks"])


@router.post("/evaluate-rollback")
async def evaluate_rollback(payload: RollbackEvaluationRequest):
    """Evaluate live cluster power spike and auto-rollback if >35% baseline spike."""
    return RollbackService.evaluate_and_rollback(
        namespace=payload.namespace,
        deployment_name=payload.deployment_name,
        current_power_w=payload.current_power_w,
        baseline_power_w=payload.baseline_power_w,
        org_id=payload.org_id or 1,
        auto_trigger=payload.auto_trigger,
    )


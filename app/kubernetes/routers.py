"""Enterprise Kubernetes Telemetry & Rollback API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.kubernetes.models import RollbackEvaluationRequest
from app.kubernetes.service import RollbackService
from app.auth.dependencies import require_permission
from app.auth.roles import Permission, Role, normalize_role

router = APIRouter(prefix="/api/kubernetes", tags=["Kubernetes & Automated Rollbacks"])


@router.post("/evaluate-rollback")
async def evaluate_rollback(
    payload: RollbackEvaluationRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXECUTE_ROLLBACK)),
):
    """Evaluate live cluster power spike and auto-rollback if >35% baseline spike.

    This is a production-critical, potentially destructive action, so it requires
    the explicit ``deploy:rollback`` permission (org_admin / superadmin only) and
    enforces the tenant boundary against the requested organization.
    """
    org_id = payload.org_id or 1
    role = normalize_role(actor.get("role"))
    if role != Role.SUPERADMIN and actor.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Tenant isolation violation: token belongs to organization "
                f"{actor.get('org_id')} but requested organization {org_id}"
            ),
        )
    return RollbackService.evaluate_and_rollback(
        namespace=payload.namespace,
        deployment_name=payload.deployment_name,
        current_power_w=payload.current_power_w,
        baseline_power_w=payload.baseline_power_w,
        org_id=org_id,
        auto_trigger=payload.auto_trigger,
    )


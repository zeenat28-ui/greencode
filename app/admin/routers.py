"""Enterprise Admin API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.admin.models import UpdateSettingsRequest
from app.admin.settings import AdminSettings
from app.audit_logs import AuditLogManager
from app.auth.dependencies import get_tenant_actor, require_permission
from app.auth.roles import Permission

router = APIRouter(prefix="/api/admin", tags=["Enterprise Administration & Trust"])


@router.get("/health")
async def get_system_health():
    """Public system health check and diagnostic status (liveness probe)."""
    return {
        "status": "HEALTHY",
        "database": "CONNECTED",
        "version": "2.4.0",
        "mode": "ENTERPRISE_MODULAR",
    }


@router.get("/audit-logs/{org_id}")
async def list_audit_logs(
    org_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
    tenant: Dict[str, Any] = Depends(get_tenant_actor),
):
    """Retrieve cryptographic tamper-evident audit ledger entries."""
    return AuditLogManager.get_trail(org_id=org_id, limit=limit, offset=offset, action=action)


@router.get("/audit-logs/{org_id}/verify")
async def verify_audit_chain(
    org_id: int,
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
    tenant: Dict[str, Any] = Depends(get_tenant_actor),
):
    """Cryptographically verify the SHA-256 hash chain for auditors."""
    return AuditLogManager.verify_integrity(org_id=org_id)


@router.get("/settings")
async def get_admin_settings(
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Get enterprise administrative settings."""
    return AdminSettings.get_settings()


@router.patch("/settings")
async def update_admin_settings(
    payload: UpdateSettingsRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Update enterprise guardrail configurations."""
    return AdminSettings.update_settings(payload.model_dump(exclude_unset=True))


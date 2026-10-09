"""Enterprise Audit REST API Router."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.audit.service import AuditService
from app.auth.dependencies import get_current_actor, require_permission
from app.auth.roles import Permission

router = APIRouter(prefix="/api/audit", tags=["Static & Dynamic Auditing"])


class ScanRequest(BaseModel):
    path: str = Field(..., description="File or directory path to audit")
    project_id: Optional[int] = Field(None, description="Project ID if associating with a project")
    commit_sha: Optional[str] = Field("HEAD", description="Commit SHA being audited")


@router.post("/scan")
async def trigger_scan(
    payload: ScanRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.TRIGGER_AUDIT)),
):
    """Trigger an AST static audit on a local directory or repository path."""
    try:
        result = AuditService.execute_audit(
            path=payload.path,
            project_id=payload.project_id,
            commit_sha=payload.commit_sha or "HEAD",
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit scan failure: {str(e)}")


@router.get("/projects/{project_id}/history")
async def get_project_audit_history(
    project_id: int,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Retrieve audit history and scores for a specific project."""
    return AuditService.get_project_audits(project_id=project_id)


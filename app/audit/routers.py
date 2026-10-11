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


class SarifExportRequest(BaseModel):
    source_code: Optional[str] = Field(None, max_length=200000, description="Source code snippet to audit and export")
    language: str = Field("python", max_length=40, description="Programming language identifier")
    filename: str = Field("snippet.py", max_length=300, description="Virtual file path for SARIF artifact location")
    path: Optional[str] = Field(None, max_length=500, description="Optional local directory or file path to audit")


def _run_scan_for_export(payload: SarifExportRequest) -> Dict[str, Any]:
    from app.parser import audit_repository, audit_source_code
    import os

    if payload.source_code is not None:
        return audit_source_code(
            payload.source_code,
            language=payload.language,
            file_path=payload.filename,
        )
    target = os.path.abspath(payload.path or ".")
    if not os.path.exists(target):
        raise HTTPException(status_code=400, detail=f"Target path does not exist: {target}")
    return audit_repository(target)


@router.post("/sarif")
async def export_sarif_report(payload: SarifExportRequest):
    """Generate an OASIS SARIF v2.1.0 report with embedded deterministic autofix replacements."""
    from app.sarif import generate_sarif_report

    scan_res = _run_scan_for_export(payload)
    return generate_sarif_report(scan_res, base_dir=scan_res.get("repo_path"))


@router.post("/sonarqube")
async def export_sonarqube_report(payload: SarifExportRequest):
    """Generate a SonarQube Generic Issue Import JSON report."""
    from app.sarif import generate_sonarqube_report

    scan_res = _run_scan_for_export(payload)
    return generate_sonarqube_report(scan_res, base_dir=scan_res.get("repo_path"))


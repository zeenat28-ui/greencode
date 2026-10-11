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
@router.post("/compare", status_code=status.HTTP_200_OK)
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


@router.post("/gitlab-preview", status_code=status.HTTP_200_OK)
async def preview_gitlab_mr_gate(payload: Dict[str, Any]):
    """Audit code or scan results and generate a GitLab Merge Request comment with suggestion:-0+0 blocks."""
    from app.gitlab_client import post_gitlab_mr_comment
    from app.parser import audit_source_code

    source_code = str(payload.get("source_code") or "")
    language = str(payload.get("language") or "python")
    file_path = str(payload.get("file_path") or "app.py")
    threshold = float(payload.get("threshold") or 75.0)
    zone = str(payload.get("zone") or "US-CAL-CISO")
    project_id = str(payload.get("project_id") or "group/repo")
    mr_iid = int(payload.get("mr_iid") or 1)
    gitlab_token = payload.get("gitlab_token")

    scan_result = payload.get("scan_result")
    if not isinstance(scan_result, dict):
        scan_result = audit_source_code(source_code, language=language, file_path=file_path)

    return post_gitlab_mr_comment(
        project_id=project_id,
        mr_iid=mr_iid,
        scan_result=scan_result,
        gitlab_token=str(gitlab_token) if gitlab_token else None,
        threshold=threshold,
        zone=zone,
    )


@router.post("/gitlab-webhook", status_code=status.HTTP_200_OK)
async def handle_gitlab_mr_webhook(payload: Dict[str, Any]):
    """Process a GitLab Merge Request webhook event (`object_kind == 'merge_request'`) and return gate status."""
    from app.gitlab_client import build_gitlab_mr_carbon_comment
    from app.parser import audit_source_code

    object_kind = str(payload.get("object_kind") or "merge_request")
    project = payload.get("project") or {}
    attrs = payload.get("object_attributes") or {}
    mr_iid = int(attrs.get("iid") or payload.get("mr_iid") or 1)
    project_path = str(project.get("path_with_namespace") or payload.get("project_id") or "gitlab-org/project")
    source_code = str(payload.get("source_code") or "")
    scan_res = audit_source_code(source_code, language="python", file_path="mr_diff.py") if source_code else {
        "green_score": 100.0,
        "violations": [],
    }
    comment_md = build_gitlab_mr_carbon_comment(scan_res)
    return {
        "event": object_kind,
        "project": project_path,
        "mr_iid": mr_iid,
        "green_score": scan_res.get("green_score", 100.0),
        "violations_count": len(scan_res.get("violations", [])),
        "comment_markdown": comment_md,
    }


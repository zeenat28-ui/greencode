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


@router.get("/plugins")
async def list_registered_plugins():
    """Return the active catalog of analyzer plugins, lifecycle hooks, and signed webhook sinks."""
    from app.plugins import plugin_registry

    return plugin_registry.list_catalog()


@router.post("/plugins/webhooks")
async def register_webhook_sink(payload: Dict[str, Any]):
    """Register an outbound webhook sink with HMAC-SHA256 payload signing."""
    from app.plugins import plugin_registry

    sink_id = str(payload.get("sink_id") or payload.get("id") or "default-sink").strip()
    target_url = str(payload.get("target_url") or "").strip()
    if not target_url:
        raise HTTPException(status_code=400, detail="target_url is required")
    events = payload.get("events")
    secret = str(payload.get("secret") or "greencode-webhook-secret")
    return plugin_registry.register_webhook_sink(
        sink_id=sink_id,
        target_url=target_url,
        events=events if isinstance(events, list) else None,
        secret=secret,
    )


@router.post("/plugins/dispatch-test")
async def dispatch_plugin_test_event(payload: Dict[str, Any]):
    """Dispatch a test lifecycle event across registered hooks and generate signed webhook envelopes."""
    from app.plugins import plugin_registry

    event_type = str(payload.get("event_type") or "audit.completed")
    event_data = payload.get("data") if isinstance(payload.get("data"), dict) else {"green_score": 100.0}
    return plugin_registry.dispatch_event(event_type=event_type, payload=event_data)


@router.post("/call-graph")
async def audit_repository_call_graph(payload: Dict[str, Any]):
    """Build a cross-file inter-procedural call graph and detect cross-module loop I/O."""
    from app.call_graph import audit_cross_file_loops

    files = payload.get("files")
    if not isinstance(files, dict) or not files:
        raise HTTPException(status_code=400, detail="files mapping {file_path: source_code} is required")
    normalized = {str(k): str(v) for k, v in files.items()}
    return audit_cross_file_loops(normalized)


@router.post("/telemetry/otlp")
async def export_otlp_telemetry(payload: Dict[str, Any]):
    """Build and optionally push an OpenTelemetry (OTLP/HTTP v1 JSON) carbon & SCI metrics payload."""
    from app.otel_exporter import build_otlp_metrics_payload, export_otlp_metrics

    otlp_payload = build_otlp_metrics_payload(
        service_name=str(payload.get("service_name") or "greencode-auditor"),
        repository=str(payload.get("repository") or "zeenat28-ui/greencode"),
        green_score=float(payload.get("green_score", 100.0)),
        energy_joules=float(payload.get("energy_joules", 25.0)),
        duration_seconds=float(payload.get("duration_seconds", 1.0)),
        functional_unit=float(payload.get("functional_unit", 1.0)),
        grid_intensity_gco2_kwh=float(payload.get("grid_intensity_gco2_kwh", 210.0)),
        zone=str(payload.get("zone") or "IE"),
        measurement_method=payload.get("measurement_method"),
    )
    return export_otlp_metrics(
        otlp_payload,
        endpoint=payload.get("endpoint"),
        headers=payload.get("headers") if isinstance(payload.get("headers"), dict) else None,
    )




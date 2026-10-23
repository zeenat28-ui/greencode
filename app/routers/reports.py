"""Enterprise ESG Reports, Compliance & Audit Trail API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse

from app.audit_logs import AuditLogManager
from app.compliance import ComplianceManager
from app.reports.esg_report import ESGReportGenerator
from app.auth.dependencies import enforce_tenant_scope, require_permission
from app.auth.roles import Permission

router = APIRouter(prefix="/api/reports", tags=["ESG Compliance & Audit Reports"])


def _authorize_report_tenant(org_id: int, actor: Dict[str, Any]) -> None:
    enforce_tenant_scope(actor, org_id, resource="compliance report")


@router.get("/esg/{org_id}")
async def get_esg_report(
    org_id: int,
    period: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Fetch structured ESG and Scope 2/3 GHG compliance report as JSON."""
    _authorize_report_tenant(org_id, actor)
    return ESGReportGenerator.generate_data(org_id=org_id, period=period)


@router.get("/esg/{org_id}/html", response_class=HTMLResponse)
@router.get("/esg/{org_id}/export/html", response_class=HTMLResponse)
async def export_esg_html(
    org_id: int,
    period: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Render exportable, audit-grade executive HTML ESG sustainability report."""
    _authorize_report_tenant(org_id, actor)
    html_content = ESGReportGenerator.generate_html(org_id=org_id, period=period)
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.get("/esg/{org_id}/csv")
async def export_esg_csv(
    org_id: int,
    period: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Render exportable CSV ESG sustainability report."""
    _authorize_report_tenant(org_id, actor)
    from app.reports.exports import ReportExporter
    return Response(
        content=ReportExporter.export_csv(org_id=org_id, period=period),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="greencode-esg-{org_id}.csv"'},
    )


@router.get("/esg/{org_id}/evidence-bundle")
async def export_esg_evidence_bundle(
    org_id: int,
    period: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Download cryptographically signed CSRD/SEC Audit Evidence ZIP archive."""
    _authorize_report_tenant(org_id, actor)
    zip_bytes, manifest = ESGReportGenerator.generate_evidence_bundle(org_id=org_id, period=period)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="greencode-csrd-evidence-org-{org_id}.zip"',
            "X-Bundle-Root-SHA256": str(manifest.get("bundle_root_sha256", "")),
        },
    )


@router.get("/esg/{org_id}/evidence-manifest")
async def get_esg_evidence_manifest(
    org_id: int,
    period: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Return SHA-256 cryptographic digest manifest for the CSRD/SEC Audit Evidence bundle."""
    _authorize_report_tenant(org_id, actor)
    _, manifest = ESGReportGenerator.generate_evidence_bundle(org_id=org_id, period=period)
    return manifest


@router.get("/audit-logs/{org_id}")
async def get_audit_trail(
    org_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Query paginated, hash-chained immutable audit log entries."""
    _authorize_report_tenant(org_id, actor)
    return AuditLogManager.get_trail(
        org_id=org_id,
        limit=limit,
        offset=offset,
        action=action,
    )


@router.get("/audit-logs/{org_id}/verify")
async def verify_audit_chain_integrity(
    org_id: int,
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Verify cryptographic SHA-256 chain continuity for enterprise compliance auditors."""
    _authorize_report_tenant(org_id, actor)
    return AuditLogManager.verify_integrity(org_id=org_id)


@router.get("/compliance/{org_id}")
async def get_compliance_posture(
    org_id: int,
    actor: Dict[str, Any] = Depends(require_permission(Permission.EXPORT_ESG)),
):
    """Audit platform security posture, SOC2 readiness, and data retention rules."""
    _authorize_report_tenant(org_id, actor)
    return ComplianceManager.evaluate_security_posture(org_id=org_id)


@router.get("/impact-framework-manifest")
async def get_gsf_impact_framework_manifest(
    component_name: str = Query("greencode-workload"),
    energy_joules: float = Query(42.5, ge=0.0),
    duration_seconds: float = Query(10.0, gt=0.0),
    grid_intensity: float = Query(320.0, ge=0.0),
    functional_unit: float = Query(100.0, gt=0.0),
    vcpu_count: int = Query(4, ge=1),
    cloud_instance: str = Query("c7g.xlarge"),
):
    """Export a Green Software Foundation Impact Framework (.imp.yaml) manifest."""
    from app.sci import export_impact_framework_manifest

    return export_impact_framework_manifest(
        component_name=component_name,
        energy_joules=energy_joules,
        duration_seconds=duration_seconds,
        carbon_intensity_gco2_per_kwh=grid_intensity,
        functional_unit=functional_unit,
        vcpu_count=vcpu_count,
        cloud_instance=cloud_instance,
    )


@router.post("/impact-framework-manifest")
async def create_gsf_impact_framework_manifest(payload: Dict[str, Any]):
    """Generate a custom Green Software Foundation Impact Framework (.imp.yaml) manifest from workload telemetry."""
    from app.sci import export_impact_framework_manifest

    return export_impact_framework_manifest(
        component_name=str(payload.get("component_name") or "greencode-workload"),
        energy_joules=float(payload.get("energy_joules") or 42.5),
        duration_seconds=float(payload.get("duration_seconds") or 10.0),
        carbon_intensity_gco2_per_kwh=float(payload.get("grid_intensity") or 320.0),
        functional_unit=float(payload.get("functional_unit") or 100.0),
        vcpu_count=int(payload.get("vcpu_count") or 4),
        cloud_instance=str(payload.get("cloud_instance") or "c7g.xlarge"),
    )

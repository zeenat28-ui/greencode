"""Enterprise Compliance & ESG Reports API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.audit_logs import AuditLogManager
from app.reports.exports import ReportExporter
from app.reports.compliance import ComplianceFormatter
from app.reports.esg_report import ESGReportGenerator

router = APIRouter(prefix="/api/reports", tags=["Compliance & Audit Reports"])


@router.get("/esg/{org_id}")
async def get_esg_report(org_id: int, period: Optional[str] = Query(None)):
    """Generate regulatory ESG sustainability disclosure for an enterprise."""
    return ComplianceFormatter.get_esg_data(org_id=org_id, period=period)


@router.get("/esg/{org_id}/html", response_class=HTMLResponse)
@router.get("/esg/{org_id}/export/html", response_class=HTMLResponse)
async def get_esg_report_html(org_id: int, period: Optional[str] = Query(None)):
    """Render standalone executive HTML disclosure certificate."""
    html_content = ComplianceFormatter.get_esg_html(org_id=org_id, period=period)
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.get("/esg/{org_id}/csv", response_class=PlainTextResponse)
async def get_esg_report_csv(org_id: int, period: Optional[str] = Query(None)):
    """Download SEC/CSRD compliance data as CSV."""
    csv_content = ReportExporter.export_csv(org_id=org_id, period=period)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=esg-report-{org_id}.csv"},
    )


@router.get("/audit-logs/{org_id}")
async def get_audit_trail(
    org_id: int,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
):
    """Query paginated, hash-chained immutable audit log entries."""
    return AuditLogManager.get_trail(
        org_id=org_id,
        limit=limit,
        offset=offset,
        action=action,
    )


@router.get("/audit-logs/{org_id}/verify")
async def verify_audit_chain_integrity(org_id: int):
    """Verify cryptographic SHA-256 chain continuity for enterprise compliance auditors."""
    return AuditLogManager.verify_integrity(org_id=org_id)


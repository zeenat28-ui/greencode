"""Enterprise ESG Reports, Compliance & Audit Trail API Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse

from app.audit_logs import AuditLogManager
from app.compliance import ComplianceManager
from app.reports.esg_report import ESGReportGenerator

router = APIRouter(prefix="/api/reports", tags=["ESG Compliance & Audit Reports"])


@router.get("/esg/{org_id}")
async def get_esg_report(org_id: int, period: Optional[str] = Query(None)):
    """Fetch structured ESG and Scope 2/3 GHG compliance report as JSON."""
    return ESGReportGenerator.generate_data(org_id=org_id, period=period)


@router.get("/esg/{org_id}/export/html", response_class=HTMLResponse)
async def export_esg_html(org_id: int, period: Optional[str] = Query(None)):
    """Render exportable, audit-grade executive HTML ESG sustainability report."""
    html_content = ESGReportGenerator.generate_html(org_id=org_id, period=period)
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


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


@router.get("/compliance/{org_id}")
async def get_compliance_posture(org_id: int):
    """Audit platform security posture, SOC2 readiness, and data retention rules."""
    return ComplianceManager.evaluate_security_posture(org_id=org_id)


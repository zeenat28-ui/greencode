"""SaaS Support & Operations REST API Router."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.support_service import SupportService
from app.auth.dependencies import get_current_actor, require_permission
from app.auth.roles import Permission

router = APIRouter(prefix="/api/support", tags=["Support"])


def _enforce_tenant(actor: Dict[str, Any], org_id: int) -> None:
    """Refuse cross-tenant support access unless the caller is a platform superadmin."""
    role = (actor.get("role") or "").lower()
    if role != "superadmin" and actor.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Tenant isolation violation: token belongs to organization "
                f"{actor.get('org_id')} but requested organization {org_id}"
            ),
        )


class CreateTicketRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    subject: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    severity: str = Field("normal", pattern="^(low|normal|high|critical)$")
    tier: str = Field("free", pattern="^(free|pro|enterprise)$")
    requester_id: Optional[int] = Field(None, gt=0)


class ListTicketsRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    limit: int = Field(50, ge=1, le=200)


@router.post(
    "/ticket",
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    payload: CreateTicketRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Open a support/ops ticket with a tier-driven SLA target."""
    _enforce_tenant(actor, payload.org_id)
    return SupportService.create_ticket(
        org_id=payload.org_id,
        subject=payload.subject,
        description=payload.description or "",
        severity=payload.severity,
        tier=payload.tier,
        requester_id=payload.requester_id,
    )


@router.get("/tickets", status_code=status.HTTP_200_OK)
async def list_tickets(
    payload: ListTicketsRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """List the tenant's support tickets, newest first."""
    _enforce_tenant(actor, payload.org_id)
    return SupportService.list_tickets(org_id=payload.org_id, limit=payload.limit)


@router.post(
    "/ticket/{ticket_id}/respond",
    status_code=status.HTTP_200_OK,
)
async def respond_ticket(
    ticket_id: int,
    org_id: int = Query(..., gt=0),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Record the first agent response and evaluate SLA compliance."""
    _enforce_tenant(actor, org_id)
    return SupportService.respond(org_id=org_id, ticket_id=ticket_id)


@router.post(
    "/ticket/{ticket_id}/resolve",
    status_code=status.HTTP_200_OK,
)
async def resolve_ticket(
    ticket_id: int,
    org_id: int = Query(..., gt=0),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Resolve a support ticket."""
    _enforce_tenant(actor, org_id)
    return SupportService.resolve(org_id=org_id, ticket_id=ticket_id)


@router.get("/plan", status_code=status.HTTP_200_OK)
async def support_plan(
    org_id: int = Query(..., gt=0),
    tier: str = Query("free", pattern="^(free|pro|enterprise)$"),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Describe the support & ops posture for a tenant's tier."""
    _enforce_tenant(actor, org_id)
    return SupportService.support_plan(org_id=org_id, tier=tier)

"""Enterprise Tenant and Organization REST API Router."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.tenants.service import TenantService
from app.auth.dependencies import get_current_actor, get_tenant_actor, require_permission
from app.auth.roles import Permission

router = APIRouter(prefix="/api/tenants", tags=["Tenant & Org Management"])


class CreateTenantOrgRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    tier: str = Field("enterprise", pattern="^(free|pro|enterprise)$")
    sso_enabled: bool = False


class CreateTeamPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    monthly_budget_kg: float = 500.0


class CreateProjectPayload(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    team_id: Optional[int] = None
    sci_threshold: float = 80.0


@router.get("/orgs")
async def list_tenants(actor: Dict[str, Any] = Depends(get_current_actor)):
    """List all enterprise tenant workspaces."""
    return TenantService.list_organizations()


@router.post("/orgs", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: CreateTenantOrgRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Create a new isolated enterprise tenant workspace."""
    return TenantService.create_organization(
        name=payload.name,
        slug=payload.slug,
        tier=payload.tier,
        sso_enabled=payload.sso_enabled,
    )


@router.get("/orgs/{org_id}")
async def get_tenant(org_id: int, actor: Dict[str, Any] = Depends(get_tenant_actor)):
    """Fetch tenant details and resource quotas."""
    org = TenantService.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Tenant organization not found")
    return org


@router.get("/orgs/{org_id}/teams")
async def list_teams(org_id: int, actor: Dict[str, Any] = Depends(get_tenant_actor)):
    """List all engineering teams belonging to this tenant."""
    return TenantService.list_teams(org_id)


@router.post("/orgs/{org_id}/teams", status_code=status.HTTP_201_CREATED)
async def create_team(
    org_id: int,
    payload: CreateTeamPayload,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_TEAMS)),
    tenant: Dict[str, Any] = Depends(get_tenant_actor),
):
    """Create an engineering team under the tenant organization."""
    return TenantService.create_team(
        org_id=org_id,
        name=payload.name,
        slug=payload.slug,
        monthly_budget_kg=payload.monthly_budget_kg,
    )


@router.get("/orgs/{org_id}/projects")
async def list_projects(
    org_id: int,
    team_id: Optional[int] = Query(None),
    actor: Dict[str, Any] = Depends(get_tenant_actor),
):
    """List monitored projects under this tenant."""
    return TenantService.list_projects(org_id=org_id, team_id=team_id)


@router.post("/orgs/{org_id}/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    org_id: int,
    payload: CreateProjectPayload,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_PROJECTS)),
    tenant: Dict[str, Any] = Depends(get_tenant_actor),
):
    """Register a new software service/project under a tenant team."""
    return TenantService.create_project(
        org_id=org_id,
        name=payload.name,
        slug=payload.slug,
        team_id=payload.team_id,
        sci_threshold=payload.sci_threshold,
    )


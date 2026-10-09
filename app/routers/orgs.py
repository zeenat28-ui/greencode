"""Enterprise Multi-Tenancy Organization & Projects REST API Router."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.org_service import OrgService

router = APIRouter(prefix="/api/orgs", tags=["Organizations & Multi-Tenancy"])


class CreateOrgRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    tier: str = Field("enterprise", pattern="^(free|pro|enterprise)$")
    sso_enabled: bool = False


class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    monthly_carbon_budget_kg: float = 500.0


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    team_id: Optional[int] = None
    repo_url: Optional[str] = None
    default_branch: str = "main"
    sci_threshold: float = 80.0
    energy_budget_kwh: float = 50.0
    policy: Optional[Dict[str, Any]] = None


class AssignMemberRequest(BaseModel):
    user_id: int
    role: str = Field("developer", pattern="^(admin|maintainer|developer|auditor)$")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(payload: CreateOrgRequest):
    """Create a new enterprise tenant organization."""
    return OrgService.create_organization(
        name=payload.name,
        slug=payload.slug,
        tier=payload.tier,
        sso_enabled=payload.sso_enabled,
    )


@router.get("/{org_id}")
async def get_organization(org_id: int):
    """Fetch organization metadata, project counts, and quotas."""
    org = OrgService.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/{org_id}/teams", status_code=status.HTTP_201_CREATED)
async def create_team(org_id: int, payload: CreateTeamRequest):
    """Create an engineering team under the tenant organization."""
    return OrgService.create_team(
        org_id=org_id,
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        monthly_carbon_budget_kg=payload.monthly_carbon_budget_kg,
    )


@router.get("/{org_id}/teams")
async def list_teams(org_id: int):
    """List all teams belonging to an organization."""
    return OrgService.list_teams(org_id)


@router.post("/{org_id}/projects", status_code=status.HTTP_201_CREATED)
async def create_project(org_id: int, payload: CreateProjectRequest):
    """Register and configure a monitored microservice or repository under an org."""
    return OrgService.create_project(
        org_id=org_id,
        name=payload.name,
        slug=payload.slug,
        team_id=payload.team_id,
        repo_url=payload.repo_url,
        default_branch=payload.default_branch,
        sci_threshold=payload.sci_threshold,
        energy_budget_kwh=payload.energy_budget_kwh,
        policy=payload.policy,
    )


@router.get("/{org_id}/projects")
async def list_projects(org_id: int, team_id: Optional[int] = Query(None)):
    """List all monitored projects under an organization, optionally filtered by team."""
    return OrgService.list_projects(org_id=org_id, team_id=team_id)


@router.post("/{org_id}/projects/{project_id}/members")
async def assign_project_member(org_id: int, project_id: int, payload: AssignMemberRequest):
    """Assign or update a user's role on a specific project."""
    return OrgService.assign_project_member(
        project_id=project_id,
        user_id=payload.user_id,
        role=payload.role,
    )


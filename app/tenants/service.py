"""Enterprise Tenant Management and Hierarchy Service."""

from typing import Any, Dict, List, Optional
from app.services.org_service import OrgService
from app.database import SessionLocal, Organization, Team, Project, User


class TenantService:
    """Service wrapping all organizational and team tenant management."""

    @classmethod
    def list_organizations(cls) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            orgs = db.query(Organization).all()
            return [
                {
                    "id": o.id,
                    "name": o.name,
                    "slug": o.slug,
                    "tier": o.tier,
                    "sso_enabled": o.sso_enabled,
                }
                for o in orgs
            ]
        finally:
            db.close()

    @classmethod
    def get_organization(cls, org_id: int) -> Optional[Dict[str, Any]]:
        return OrgService.get_organization(org_id)

    @classmethod
    def create_organization(cls, name: str, slug: str, tier: str = "enterprise", sso_enabled: bool = False) -> Dict[str, Any]:
        return OrgService.create_organization(name=name, slug=slug, tier=tier, sso_enabled=sso_enabled)

    @classmethod
    def create_team(cls, org_id: int, name: str, slug: str, monthly_budget_kg: float = 500.0) -> Dict[str, Any]:
        return OrgService.create_team(org_id=org_id, name=name, slug=slug, monthly_carbon_budget_kg=monthly_budget_kg)

    @classmethod
    def list_teams(cls, org_id: int) -> List[Dict[str, Any]]:
        return OrgService.list_teams(org_id)

    @classmethod
    def create_project(cls, org_id: int, name: str, slug: str, team_id: Optional[int] = None, sci_threshold: float = 80.0) -> Dict[str, Any]:
        return OrgService.create_project(org_id=org_id, team_id=team_id, name=name, slug=slug, sci_threshold=sci_threshold)

    @classmethod
    def list_projects(cls, org_id: int, team_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return OrgService.list_projects(org_id=org_id, team_id=team_id)

    @classmethod
    def assign_member(cls, project_id: int, user_id: int, role: str = "developer") -> Dict[str, Any]:
        return OrgService.assign_project_member(project_id=project_id, user_id=user_id, role=role)


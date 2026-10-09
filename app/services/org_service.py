"""Enterprise Multi-Tenancy Organization & Project Service.

Manages tenant isolation, organizations, teams, microservice projects,
user role memberships, and governance boundaries.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from app.database import (
    AuditLog,
    Organization,
    Project,
    ProjectMember,
    SessionLocal,
    Team,
    User,
)
from app.auth.roles import Role, normalize_role

logger = logging.getLogger("greencode.services.org")


class OrgService:
    """Service layer orchestrating multi-tenant hierarchy and permissions."""

    @staticmethod
    def create_organization(
        name: str,
        slug: str,
        tier: str = "enterprise",
        sso_enabled: bool = False,
    ) -> Dict[str, Any]:
        """Create a new enterprise tenant organization."""
        db: Session = SessionLocal()
        try:
            existing = db.query(Organization).filter(Organization.slug == slug).first()
            if existing:
                return {
                    "id": existing.id,
                    "name": existing.name,
                    "slug": existing.slug,
                    "tier": existing.tier,
                    "sso_enabled": existing.sso_enabled,
                    "created_at": existing.created_at.isoformat(),
                }

            org = Organization(
                name=name,
                slug=slug,
                tier=tier,
                sso_enabled=sso_enabled,
            )
            db.add(org)
            db.commit()
            db.refresh(org)

            # Record audit event
            audit = AuditLog(
                org_id=org.id,
                action="org:create",
                resource_type="organization",
                resource_id=str(org.id),
                status="SUCCESS",
                details=json.dumps({"name": name, "tier": tier}),
            )
            db.add(audit)
            db.commit()

            return {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "tier": org.tier,
                "sso_enabled": org.sso_enabled,
                "created_at": org.created_at.isoformat(),
            }
        finally:
            db.close()

    @staticmethod
    def get_organization(org_id: int) -> Optional[Dict[str, Any]]:
        """Fetch organization profile and metrics."""
        db: Session = SessionLocal()
        try:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            if not org:
                return None
            teams_count = db.query(Team).filter(Team.org_id == org_id).count()
            projects_count = db.query(Project).filter(Project.org_id == org_id).count()
            users_count = db.query(User).filter(User.org_id == org_id).count()
            return {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "tier": org.tier,
                "sso_enabled": org.sso_enabled,
                "teams_count": teams_count,
                "projects_count": projects_count,
                "users_count": users_count,
                "created_at": org.created_at.isoformat(),
            }
        finally:
            db.close()

    @staticmethod
    def create_team(
        org_id: int,
        name: str,
        slug: str,
        description: Optional[str] = None,
        monthly_carbon_budget_kg: float = 500.0,
    ) -> Dict[str, Any]:
        """Create an engineering team under an organization."""
        db: Session = SessionLocal()
        try:
            team = Team(
                org_id=org_id,
                name=name,
                slug=slug,
                description=description,
                monthly_carbon_budget_kg=monthly_carbon_budget_kg,
            )
            db.add(team)
            db.commit()
            db.refresh(team)
            return {
                "id": team.id,
                "org_id": team.org_id,
                "name": team.name,
                "slug": team.slug,
                "description": team.description,
                "monthly_carbon_budget_kg": team.monthly_carbon_budget_kg,
                "created_at": team.created_at.isoformat(),
            }
        finally:
            db.close()

    @staticmethod
    def list_teams(org_id: int) -> List[Dict[str, Any]]:
        """List all teams configured within a tenant organization."""
        db: Session = SessionLocal()
        try:
            teams = db.query(Team).filter(Team.org_id == org_id).all()
            return [
                {
                    "id": t.id,
                    "org_id": t.org_id,
                    "name": t.name,
                    "slug": t.slug,
                    "description": t.description,
                    "monthly_carbon_budget_kg": t.monthly_carbon_budget_kg,
                    "created_at": t.created_at.isoformat(),
                }
                for t in teams
            ]
        finally:
            db.close()

    @staticmethod
    def create_project(
        org_id: int,
        name: str,
        slug: str,
        team_id: Optional[int] = None,
        repo_url: Optional[str] = None,
        default_branch: str = "main",
        sci_threshold: float = 80.0,
        energy_budget_kwh: float = 50.0,
        policy: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create and configure a monitored software project or service."""
        db: Session = SessionLocal()
        try:
            project = Project(
                org_id=org_id,
                team_id=team_id,
                name=name,
                slug=slug,
                repo_url=repo_url,
                default_branch=default_branch,
                sci_threshold=sci_threshold,
                energy_budget_kwh=energy_budget_kwh,
                policy_json=json.dumps(policy or {}),
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            return {
                "id": project.id,
                "org_id": project.org_id,
                "team_id": project.team_id,
                "name": project.name,
                "slug": project.slug,
                "repo_url": project.repo_url,
                "default_branch": project.default_branch,
                "sci_threshold": project.sci_threshold,
                "energy_budget_kwh": project.energy_budget_kwh,
                "created_at": project.created_at.isoformat(),
            }
        finally:
            db.close()

    @staticmethod
    def list_projects(org_id: int, team_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List monitored projects under an organization or team."""
        db: Session = SessionLocal()
        try:
            query = db.query(Project).filter(Project.org_id == org_id)
            if team_id is not None:
                query = query.filter(Project.team_id == team_id)
            projects = query.all()
            return [
                {
                    "id": p.id,
                    "org_id": p.org_id,
                    "team_id": p.team_id,
                    "name": p.name,
                    "slug": p.slug,
                    "repo_url": p.repo_url,
                    "default_branch": p.default_branch,
                    "sci_threshold": p.sci_threshold,
                    "energy_budget_kwh": p.energy_budget_kwh,
                    "created_at": p.created_at.isoformat(),
                }
                for p in projects
            ]
        finally:
            db.close()

    @staticmethod
    def assign_project_member(
        project_id: int,
        user_id: int,
        role: str = "developer",
    ) -> Dict[str, Any]:
        """Assign or update a user's role on a specific project."""
        db: Session = SessionLocal()
        try:
            member = (
                db.query(ProjectMember)
                .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
                .first()
            )
            if member:
                member.role = role
            else:
                member = ProjectMember(
                    project_id=project_id,
                    user_id=user_id,
                    role=role,
                )
                db.add(member)
            db.commit()
            db.refresh(member)
            return {
                "id": member.id,
                "project_id": member.project_id,
                "user_id": member.user_id,
                "role": member.role,
                "created_at": member.created_at.isoformat(),
            }
        finally:
            db.close()


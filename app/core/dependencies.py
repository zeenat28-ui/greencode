"""Enterprise Dependency Injection and Request Scoping."""

from typing import Any, Callable, Dict, Optional
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.roles import Permission, has_permission, normalize_role
from app.core.database import get_db
from app.core.exceptions import TenantNotFoundException, PermissionDeniedException
from app.database import Organization, User


async def get_current_org(
    request: Request,
    x_org_id: Optional[str] = Header(None, alias="X-Org-ID"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Extract and validate the active Tenant Organization from headers or JWT state."""
    org_id_val = x_org_id or getattr(request.state, "org_id", 1)
    try:
        org_id = int(org_id_val)
    except (TypeError, ValueError):
        org_id = 1

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        # Fallback to default enterprise org if in setup mode
        org = db.query(Organization).first()
        if not org:
            org = Organization(name="Default Enterprise", slug="default-org", tier="enterprise")
            db.add(org)
            db.commit()
            db.refresh(org)

    request.state.org_id = org.id
    request.state.org = org
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "tier": org.tier,
    }


def require_permission(perm: Permission) -> Callable:
    """Dependency factory checking that the caller holds the specified permission."""

    async def _perm_checker(
        request: Request,
        org: Dict[str, Any] = Depends(get_current_org),
    ) -> Dict[str, Any]:
        user_role = getattr(request.state, "user_role", "org_admin")
        if not has_permission(user_role, perm):
            raise PermissionDeniedException(action=perm.value, role=str(user_role))
        return {"role": user_role, "org_id": org["id"]}

    return _perm_checker


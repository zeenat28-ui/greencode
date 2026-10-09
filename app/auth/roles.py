"""Role-Based Access Control (RBAC) System for GreenCode Enterprise.

Defines enterprise security roles, granular system permissions, and FastAPI
dependency injection guards for tenant isolation and governance operations.
"""

from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

bearer_scheme = HTTPBearer(auto_error=False)


class Role(str, Enum):
    """Hierarchical platform and tenant roles."""

    SUPERADMIN = "superadmin"
    ORG_ADMIN = "org_admin"
    TEAM_LEAD = "team_lead"
    DEVELOPER = "developer"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Granular enterprise actions and privileges."""

    READ_METRICS = "metrics:read"
    TRIGGER_AUDIT = "audit:trigger"
    CONFIGURE_BUDGET = "budget:configure"
    APPROVE_DEPLOY = "deploy:approve"
    EXECUTE_ROLLBACK = "deploy:rollback"
    EXPORT_ESG = "esg:export"
    MANAGE_ORG = "org:manage"
    MANAGE_USERS = "users:manage"
    MANAGE_TEAMS = "teams:manage"
    MANAGE_PROJECTS = "projects:manage"
    OVERRIDE_POLICIES = "policy:override"


# Role to Granted Permissions mapping matrix
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPERADMIN: {
        Permission.READ_METRICS,
        Permission.TRIGGER_AUDIT,
        Permission.CONFIGURE_BUDGET,
        Permission.APPROVE_DEPLOY,
        Permission.EXECUTE_ROLLBACK,
        Permission.EXPORT_ESG,
        Permission.MANAGE_ORG,
        Permission.MANAGE_USERS,
        Permission.MANAGE_TEAMS,
        Permission.MANAGE_PROJECTS,
        Permission.OVERRIDE_POLICIES,
    },
    Role.ORG_ADMIN: {
        Permission.READ_METRICS,
        Permission.TRIGGER_AUDIT,
        Permission.CONFIGURE_BUDGET,
        Permission.APPROVE_DEPLOY,
        Permission.EXECUTE_ROLLBACK,
        Permission.EXPORT_ESG,
        Permission.MANAGE_ORG,
        Permission.MANAGE_USERS,
        Permission.MANAGE_TEAMS,
        Permission.MANAGE_PROJECTS,
    },
    Role.TEAM_LEAD: {
        Permission.READ_METRICS,
        Permission.TRIGGER_AUDIT,
        Permission.CONFIGURE_BUDGET,
        Permission.APPROVE_DEPLOY,
        Permission.EXECUTE_ROLLBACK,
        Permission.EXPORT_ESG,
        Permission.MANAGE_PROJECTS,
    },
    Role.DEVELOPER: {
        Permission.READ_METRICS,
        Permission.TRIGGER_AUDIT,
    },
    Role.AUDITOR: {
        Permission.READ_METRICS,
        Permission.EXPORT_ESG,
    },
    Role.VIEWER: {
        Permission.READ_METRICS,
    },
}


def normalize_role(role_val: Optional[str]) -> Role:
    """Safely cast string representation to Role enum with developer fallback."""
    if not role_val:
        return Role.DEVELOPER
    role_str = str(role_val).strip().lower()
    for r in Role:
        if r.value == role_str or r.name.lower() == role_str:
            return r
    # Fallback mappings for legacy roles
    if role_str in ("admin", "administrator"):
        return Role.ORG_ADMIN
    if role_str in ("engineer", "dev"):
        return Role.DEVELOPER
    return Role.DEVELOPER


def has_permission(role: Optional[str], permission: Permission) -> bool:
    """Evaluate if a role possesses the specified permission."""
    r_enum = normalize_role(role)
    perms = ROLE_PERMISSIONS.get(r_enum, set())
    return permission in perms


def get_role_permissions(role: Optional[str]) -> List[str]:
    """Return all granted permission strings for a given role."""
    r_enum = normalize_role(role)
    return [p.value for p in ROLE_PERMISSIONS.get(r_enum, set())]


def check_user_permission(user: Dict[str, Any], permission: Permission) -> bool:
    """Check if user dictionary (from DB or JWT token) has a permission."""
    if not user:
        return False
    user_role = user.get("role")
    return has_permission(user_role, permission)


def require_role(*allowed_roles: str) -> Callable:
    """FastAPI dependency to enforce that user belongs to allowed roles.

    Security note: this now REQUIRES authentication. The previous version
    silently injected a ``org_admin`` context whenever no ``Authorization``
    header was present, which made every guarded route world-writable. Prefer
    :func:`app.auth.dependencies.require_role`, which is the canonical guard.
    """

    normalized_allowed = {normalize_role(r) for r in allowed_roles}

    async def _role_guard(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    ) -> Dict[str, Any]:
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        from app.auth.jwt import verify_token

        payload = verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_role = normalize_role(payload.get("role"))
        if user_role not in normalized_allowed and Role.SUPERADMIN not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{user_role.value}' lacks required role privileges {list(allowed_roles)}",
            )
        return {
            "id": int(payload.get("sub") or 0),
            "role": user_role.value,
            "org_id": int(payload.get("org_id") or 0),
        }

    return _role_guard


def require_permission(permission: Permission) -> Callable:
    """FastAPI dependency to enforce fine-grained capability checks.

    Security note: this now REQUIRES authentication (no unauthenticated
    ``superadmin`` fallback). Prefer :func:`app.auth.dependencies.require_permission`.
    """

    async def _perm_guard(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    ) -> Dict[str, Any]:
        if not credentials or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        from app.auth.jwt import verify_token

        payload = verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_role = normalize_role(payload.get("role"))
        if permission not in ROLE_PERMISSIONS.get(user_role, set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Required permission '{permission.value}' not granted to role '{user_role.value}'",
            )
        return {
            "id": int(payload.get("sub") or 0),
            "role": user_role.value,
            "org_id": int(payload.get("org_id") or 0),
        }

    return _perm_guard


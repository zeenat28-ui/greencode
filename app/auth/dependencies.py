"""Canonical Enterprise Authentication, Authorization & Tenant-Isolation Dependencies.

This module is the SINGLE source of truth for guarding the enterprise surface
(organizations, teams, projects, policies, budgets, Kubernetes rollbacks,
admin & audit endpoints).

It replaces three divergent, backdoored guards that previously shipped:
  - ``app.auth.roles.require_role / require_permission``  (returned a
    superadmin/org_admin context when NO Authorization header was present)
  - ``app.core.dependencies.require_permission``           (defaulted every
    caller to ``org_admin`` via ``getattr(request.state, "user_role", ...)``)
  - ``Depends(lambda: None)`` placeholders in the governance router

Security model:
  1. Every protected route requires a valid, unrevoked Bearer access token.
  2. The caller's tenant is taken from the VERIFIED token - never from a
     client-supplied query/body/path value. Cross-tenant access is refused
     unless the caller is a platform ``superadmin``.
  3. Fine-grained checks use the ``ROLE_PERMISSIONS`` matrix in
     ``app.auth.roles`` so there is exactly one role -> permission mapping.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.jwt import verify_token
from app.auth.roles import ROLE_PERMISSIONS, Permission, Role, normalize_role

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def get_current_actor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """Validate the Bearer token and return the authenticated actor context.

    Raises 401 for missing / malformed / expired / revoked / wrong-type tokens.
    There is deliberately NO unauthenticated fallback.
    """
    if not credentials or not credentials.credentials:
        raise _unauthorized("Authentication required: missing Bearer access token")

    payload = verify_token(credentials.credentials)
    if not payload:
        raise _unauthorized("Invalid or expired access token")

    # A refresh token must never be accepted where an access token is expected.
    if payload.get("type") == "refresh":
        raise _unauthorized("Refresh tokens cannot be used as access tokens")

    subject = payload.get("sub")
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise _unauthorized("Token subject claim is not a valid user id")

    try:
        org_id = int(payload.get("org_id") or 0)
    except (TypeError, ValueError):
        org_id = 0

    role = normalize_role(payload.get("role"))
    return {
        "user_id": user_id,
        "org_id": org_id,
        "role": role.value,
        "username": payload.get("username") or f"user-{user_id}",
    }


def require_permission(permission: Permission):
    """Dependency factory enforcing a single, canonical RBAC permission."""

    async def _guard(
        actor: Dict[str, Any] = Depends(get_current_actor),
    ) -> Dict[str, Any]:
        role = normalize_role(actor.get("role"))
        if permission not in ROLE_PERMISSIONS.get(role, set()):
            raise _forbidden(
                f"Permission '{permission.value}' is not granted to role '{role.value}'"
            )
        return actor

    return _guard


def require_role(*allowed_roles: Role):
    """Dependency factory enforcing one of the allowed roles (superadmin always passes)."""

    async def _guard(
        actor: Dict[str, Any] = Depends(get_current_actor),
    ) -> Dict[str, Any]:
        role = normalize_role(actor.get("role"))
        if role == Role.SUPERADMIN or role in allowed_roles:
            return actor
        raise _forbidden(
            f"Role '{role.value}' is not permitted; required one of "
            f"{[r.value for r in allowed_roles]}"
        )

    return _guard


async def get_tenant_actor(
    request: Request,
    org_id: int = Path(..., description="Tenant organization id"),
    actor: Dict[str, Any] = Depends(get_current_actor),
) -> Dict[str, Any]:
    """Enforce the tenant boundary for ``/api/.../{org_id}/...`` routes.

    The caller may only act inside their own organization unless they are a
    platform ``superadmin``. This is what makes multi-tenancy real: a valid
    token for tenant A can never read or mutate tenant B's data.
    """
    role = normalize_role(actor.get("role"))
    if role != Role.SUPERADMIN and actor.get("org_id") != org_id:
        raise _forbidden(
            f"Tenant isolation violation: token belongs to organization "
            f"{actor.get('org_id')} but requested organization {org_id}"
        )
    # Expose the authoritative org on the request for downstream services.
    request.state.org_id = org_id
    request.state.actor = actor
    return actor

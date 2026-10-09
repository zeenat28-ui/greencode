"""Backward-compatibility re-export shim.

The canonical, single-source-of-truth implementation of the enterprise
authentication, authorization and tenant-isolation guards now lives in
:mod:`app.auth.dependencies`. This module previously contained a *second*,
independent copy of that logic which could silently drift out of sync. It is
retained only so that any legacy ``from app.core.dependencies import ...``
statements keep working; everything is re-exported from the canonical module.
"""

from app.auth.dependencies import (  # noqa: F401
    bearer_scheme,
    get_current_actor,
    get_tenant_actor,
    require_permission,
    require_role,
)

__all__ = [
    "bearer_scheme",
    "get_current_actor",
    "get_tenant_actor",
    "require_permission",
    "require_role",
]

"""Versioned API router (v1).

Re-exports the v2 routes with deprecation warnings.  This allows external
clients to migrate at their own pace while the internal API remains on the
latest version.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Dict, Any

v1_router = APIRouter(prefix="/api/v1", tags=["API v1 (deprecated)"])


@v1_router.get("/{path:path}", response_class=JSONResponse)
async def v1_deprecated_get(path: str):
    """All v1 routes are deprecated.  Clients should migrate to /api/v2/.

    Returns a 301 redirect hint to the v2 equivalent.
    """
    return JSONResponse(
        status_code=301,
        headers={"Location": f"/api/v2/{path}", "X-API-Version": "deprecated"},
        content={
            "success": False,
            "error": "Gone",
            "message": "This v1 endpoint is deprecated. Use /api/v2/ instead.",
            "redirect": f"/api/v2/{path}",
        },
    )


@v1_router.post("/{path:path}", response_class=JSONResponse)
async def v1_deprecated_post(path: str):
    """All v1 routes are deprecated.  Clients should migrate to /api/v2/."""
    return JSONResponse(
        status_code=301,
        headers={"Location": f"/api/v2/{path}", "X-API-Version": "deprecated"},
        content={
            "success": False,
            "error": "Gone",
            "message": "This v1 endpoint is deprecated. Use /api/v2/ instead.",
            "redirect": f"/api/v2/{path}",
        },
    )

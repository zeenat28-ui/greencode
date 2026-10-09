"""Tenant Context Injection Middleware."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.database import SessionLocal, Organization


class TenantMiddleware(BaseHTTPMiddleware):
    """Intercepts requests to populate request.state.org_id and guarantee multi-tenant scoping."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        header_val = request.headers.get("X-Org-ID")
        org_id = 1
        if header_val:
            try:
                org_id = int(header_val)
            except ValueError:
                org_id = 1

        request.state.org_id = org_id

        # Attach tenant object if available
        db = SessionLocal()
        try:
            org = db.query(Organization).filter(Organization.id == org_id).first()
            request.state.org = org
        finally:
            db.close()

        response = await call_next(request)
        response.headers["X-Tenant-Org-ID"] = str(org_id)
        return response


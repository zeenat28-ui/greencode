"""Enterprise Custom Application Exceptions."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception with error code and structured metadata."""

    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An internal enterprise error occurred",
        code: str = "INTERNAL_ERROR",
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail={"message": detail, "code": code, "extra": extra or {}})
        self.code = code
        self.extra = extra or {}


class TenantNotFoundException(AppException):
    def __init__(self, org_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant Organization ID {org_id} not found or deactivated.",
            code="TENANT_NOT_FOUND",
        )


class PermissionDeniedException(AppException):
    def __init__(self, action: str, role: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' is not authorized to perform action '{action}'.",
            code="PERMISSION_DENIED",
        )


class PolicyViolationException(AppException):
    def __init__(self, message: str, delta_pct: float):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
            code="POLICY_REGRESSION_BLOCKED",
            extra={"delta_pct": delta_pct},
        )


class BudgetExceededException(AppException):
    def __init__(self, team_id: str, limit_kg: float, consumed_kg: float):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Team '{team_id}' has exceeded its monthly carbon quota ({consumed_kg:.1f}kg / {limit_kg:.1f}kg).",
            code="CARBON_BUDGET_BREACHED",
            extra={"team_id": team_id, "limit_kg": limit_kg, "consumed_kg": consumed_kg},
        )


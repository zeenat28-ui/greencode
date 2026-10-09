"""Enterprise Carbon Budget and Forecasting Service.

Implements multi-tenant organizational and team-level carbon quotas,
threshold-based alerts (70% warning, 90% critical, 100% breached),
and automated pre-deployment PR impact evaluations.
"""

from calendar import monthrange
from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from app.database import (
    AuditLog,
    CarbonBudget,
    SessionLocal,
    get_team_carbon_budget,
    record_carbon_consumption,
    set_team_carbon_budget,
)

logger = logging.getLogger("greencode.services.budget")


class BudgetService:
    """Manages carbon allocations, consumption velocity, and breach gatekeeping."""

    @staticmethod
    def _current_period() -> str:
        """Return current YYYY-MM period."""
        return datetime.now(timezone.utc).strftime("%Y-%m")

    @classmethod
    def allocate_budget(
        cls,
        org_id: int,
        team_id: str,
        monthly_budget_kg: float,
        period: Optional[str] = None,
        alert_threshold_pct: float = 80.0,
    ) -> Dict[str, Any]:
        """Allocate or adjust monthly carbon budget for an engineering team."""
        period = period or cls._current_period()
        budget = set_team_carbon_budget(
            org_id=org_id,
            team_id=team_id,
            monthly_budget_kg=monthly_budget_kg,
            period=period,
        )

        db: Session = SessionLocal()
        try:
            audit = AuditLog(
                org_id=org_id,
                action="budget:allocate",
                resource_type="carbon_budget",
                resource_id=f"{team_id}:{period}",
                status="SUCCESS",
                details=json.dumps({
                    "team_id": team_id,
                    "monthly_budget_kg": monthly_budget_kg,
                    "period": period,
                }),
            )
            db.add(audit)
            db.commit()
        finally:
            db.close()

        return budget

    @classmethod
    def record_emission(
        cls,
        org_id: int,
        team_id: str,
        consumed_kg: float,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record real-world or modeled carbon consumption for a team."""
        period = period or cls._current_period()
        result = record_carbon_consumption(
            org_id=org_id,
            team_id=team_id,
            consumed_kg=consumed_kg,
            period=period,
        )
        return result

    @classmethod
    def get_team_status(
        cls,
        org_id: int,
        team_id: str,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive budget consumption, burn rate, and alert level."""
        period = period or cls._current_period()
        budget = get_team_carbon_budget(org_id, team_id, period)

        now = datetime.now(timezone.utc)
        year, month = map(int, period.split("-"))
        _, days_in_month = monthrange(year, month)
        current_day = now.day if (now.year == year and now.month == month) else days_in_month
        days_elapsed = max(1, current_day)

        limit_kg = budget["monthly_budget_kg_co2e"]
        consumed_kg = budget["consumed_kg_co2e"]
        remaining_kg = max(0.0, round(limit_kg - consumed_kg, 4))
        consumption_pct = round((consumed_kg / max(limit_kg, 1e-6)) * 100.0, 2)

        # Burn rate and forecast
        daily_burn_rate = round(consumed_kg / days_elapsed, 4)
        forecast_month_end_kg = round(daily_burn_rate * days_in_month, 2)
        forecast_breach = forecast_month_end_kg > limit_kg

        # Alert level categorisation
        if consumption_pct >= 100.0:
            alert_level = "BREACHED"
            alert_severity = "CRITICAL"
        elif consumption_pct >= 90.0:
            alert_level = "CRITICAL"
            alert_severity = "HIGH"
        elif consumption_pct >= 70.0:
            alert_level = "WARNING"
            alert_severity = "MEDIUM"
        else:
            alert_level = "NORMAL"
            alert_severity = "INFO"

        return {
            "org_id": org_id,
            "team_id": team_id,
            "period": period,
            "monthly_budget_kg_co2e": limit_kg,
            "consumed_kg_co2e": consumed_kg,
            "remaining_kg_co2e": remaining_kg,
            "consumption_pct": consumption_pct,
            "daily_burn_rate_kg": daily_burn_rate,
            "forecast_month_end_kg": forecast_month_end_kg,
            "forecast_breach": forecast_breach,
            "alert_level": alert_level,
            "alert_severity": alert_severity,
            "is_breached": budget.get("is_breached", False) or consumption_pct >= 100.0,
        }

    @classmethod
    def evaluate_pr_impact(
        cls,
        org_id: int,
        team_id: str,
        additional_projected_kg_co2e: float,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Pre-deployment gate: test if incoming PR will violate team carbon budget."""
        status = cls.get_team_status(org_id, team_id, period)
        new_projected_consumed = status["consumed_kg_co2e"] + additional_projected_kg_co2e
        limit_kg = status["monthly_budget_kg_co2e"]
        new_pct = round((new_projected_consumed / max(limit_kg, 1e-6)) * 100.0, 2)

        will_breach = new_projected_consumed > limit_kg
        blocks_merge = will_breach or new_pct >= 100.0

        return {
            "current_status": status,
            "additional_projected_kg_co2e": additional_projected_kg_co2e,
            "projected_total_kg_co2e": round(new_projected_consumed, 4),
            "projected_consumption_pct": new_pct,
            "will_breach": will_breach,
            "blocks_merge": blocks_merge,
            "verdict": "BLOCKED" if blocks_merge else ("WARNING" if new_pct >= 85.0 else "PASSED"),
            "reason": (
                f"PR emissions (+{additional_projected_kg_co2e:.3f} kg) would breach monthly team budget of {limit_kg} kg CO2e"
                if blocks_merge
                else "PR within monthly team carbon quota"
            ),
        }


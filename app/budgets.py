"""Enterprise Team & Service Carbon Budget System.

Manages organizational, team, and project-level carbon and cloud financial budgets,
calculates burn trends, and forecasts potential overruns before deployment.
"""

from calendar import monthrange
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.services.budget_service import BudgetService
from app.database import CarbonBudget, SessionLocal

logger = logging.getLogger("greencode.budgets")


class CarbonBudgetManager:
    """Manages team and project carbon and financial cost budgets."""

    @classmethod
    def set_budget(
        cls,
        org_id: int,
        team_id: str,
        monthly_budget_kg: float,
        annual_cost_usd_budget: Optional[float] = None,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Allocate team or service carbon budget and associated cloud financial quota."""
        budget_record = BudgetService.allocate_budget(
            org_id=org_id,
            team_id=team_id,
            monthly_budget_kg=monthly_budget_kg,
            period=period,
        )
        if annual_cost_usd_budget is not None:
            budget_record["annual_cost_usd_budget"] = annual_cost_usd_budget
        return budget_record

    @classmethod
    def calculate_forecast(
        cls,
        consumed_kg: float,
        budget_kg: float,
        year: int,
        month: int,
        day: int,
    ) -> Dict[str, Any]:
        """Project end-of-month overrun based on day-of-month velocity."""
        _, days_in_month = monthrange(year, month)
        days_elapsed = max(1, day)
        daily_burn_kg = consumed_kg / days_elapsed
        projected_month_end_kg = round(daily_burn_kg * days_in_month, 2)
        projected_overrun_kg = max(0.0, round(projected_month_end_kg - budget_kg, 2))
        projected_cost_overrun_usd = round(projected_overrun_kg * 4.5, 2)  # ~$4.50/kg equivalent in compute

        will_overrun = projected_month_end_kg > budget_kg
        burn_velocity_tier = "ACCELERATING" if daily_burn_kg > (budget_kg / days_in_month) * 1.2 else "ON_TRACK"

        return {
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
            "daily_burn_kg": round(daily_burn_kg, 3),
            "projected_month_end_kg": projected_month_end_kg,
            "projected_overrun_kg": projected_overrun_kg,
            "projected_cost_overrun_usd": projected_cost_overrun_usd,
            "will_overrun": will_overrun,
            "burn_velocity_tier": burn_velocity_tier,
        }

    @classmethod
    def get_team_burn_summary(
        cls,
        org_id: int,
        team_id: str,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieve full status, burn rate, and forecasted overrun for team or CFO dashboard."""
        status = BudgetService.get_team_status(org_id=org_id, team_id=team_id, period=period)
        now = datetime.now(timezone.utc)
        forecast = cls.calculate_forecast(
            consumed_kg=status["consumed_kg_co2e"],
            budget_kg=status["monthly_budget_kg_co2e"],
            year=now.year,
            month=now.month,
            day=now.day,
        )
        status["forecast_metrics"] = forecast
        return status


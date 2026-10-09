"""Energy Debt & Carbon Accounting Tracker for Engineering Teams.

Treats energy anti-patterns and un-optimized pipelines as financial debt with
accumulating interest, providing CFOs and Engineering Leaders with team-level
accountability and ROI modeling.

Features:
- Tracks total accumulated Energy Debt (kg CO2e and USD).
- Computes Debt Velocity (interest accruing from unfixed regressions).
- Provides Team & Service Level attribution and debt pay-off tracking.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional


@dataclass
class TeamEnergyDebt:
    """Aggregated Energy Debt summary for an engineering department or team."""
    team_id: str
    team_name: str
    total_violations_count: int
    energy_debt_kg_co2e: float
    energy_debt_usd: float
    weekly_interest_usd: float
    debt_velocity_trend: str  # "ACCUMULATING", "STABLE", "PAYING_DOWN"
    top_offending_patterns: List[Dict[str, Any]]
    last_updated: str


class EnergyDebtTracker:
    """Enterprise Energy Debt & Liability Engine."""

    # Financial model: cost of cloud waste + carbon offsets liability
    COST_PER_KG_CO2E_USD = 0.085  # Real cost including electricity + verified carbon removal credits
    WEEKLY_INTEREST_RATE = 0.025  # 2.5% compounding drag on cloud OPEX

    def __init__(self):
        self._team_debts: Dict[str, TeamEnergyDebt] = {}

    def calculate_team_debt(
        self,
        team_id: str,
        team_name: str,
        violations: List[Dict[str, Any]],
        historical_debt_usd: Optional[float] = None,
    ) -> TeamEnergyDebt:
        """Compute accumulated energy debt and interest for an engineering team."""
        total_kg = 0.0
        total_usd = 0.0
        pattern_breakdown: Dict[str, int] = {}

        for v in violations:
            sev = v.get("severity", "MEDIUM")
            # Severity mapping to annual waste
            if sev == "CRITICAL":
                kg = 1330.0
                usd = 420.0
            elif sev == "HIGH":
                kg = 585.0
                usd = 185.0
            elif sev == "MEDIUM":
                kg = 205.0
                usd = 65.0
            else:
                kg = 45.0
                usd = 15.0

            total_kg += kg
            total_usd += usd
            ptype = v.get("title", v.get("violation_type", "Inefficiency"))
            pattern_breakdown[ptype] = pattern_breakdown.get(ptype, 0) + 1

        weekly_interest = total_usd * self.WEEKLY_INTEREST_RATE

        trend = "STABLE"
        if historical_debt_usd is not None:
            if total_usd > historical_debt_usd * 1.05:
                trend = "ACCUMULATING"
            elif total_usd < historical_debt_usd * 0.95:
                trend = "PAYING_DOWN"

        sorted_patterns = [
            {"pattern": k, "count": v}
            for k, v in sorted(pattern_breakdown.items(), key=lambda item: item[1], reverse=True)[:5]
        ]

        debt = TeamEnergyDebt(
            team_id=team_id,
            team_name=team_name,
            total_violations_count=len(violations),
            energy_debt_kg_co2e=round(total_kg, 2),
            energy_debt_usd=round(total_usd, 2),
            weekly_interest_usd=round(weekly_interest, 2),
            debt_velocity_trend=trend,
            top_offending_patterns=sorted_patterns,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )

        self._team_debts[team_id] = debt

        # Persist to database if available
        try:
            from app.database import EnergyDebtLedger, SessionLocal, init_db
            init_db()
            db = SessionLocal()
            try:
                row = db.query(EnergyDebtLedger).filter(
                    EnergyDebtLedger.team_id == team_id,
                ).first()
                if not row:
                    row = EnergyDebtLedger(
                        org_id=1,
                        team_id=team_id,
                        total_violations_count=len(violations),
                        energy_debt_kg_co2e=round(total_kg, 2),
                        energy_debt_usd=round(total_usd, 2),
                        weekly_interest_usd=round(weekly_interest, 2),
                        debt_velocity_trend=trend,
                        details_json=json.dumps(sorted_patterns),
                    )
                    db.add(row)
                else:
                    row.total_violations_count = len(violations)
                    row.energy_debt_kg_co2e = round(total_kg, 2)
                    row.energy_debt_usd = round(total_usd, 2)
                    row.weekly_interest_usd = round(weekly_interest, 2)
                    row.debt_velocity_trend = trend
                    row.details_json = json.dumps(sorted_patterns)
                    row.last_updated_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        except Exception:
            pass

        return debt

    def get_team_debt(self, team_id: str) -> Optional[TeamEnergyDebt]:
        return self._team_debts.get(team_id)

    def list_all_debts(self) -> List[TeamEnergyDebt]:
        return list(self._team_debts.values())


# Global singleton instance
energy_debt_tracker = EnergyDebtTracker()


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
    """Enterprise Energy Debt & Liability Engine backed by CalibratedEnergyModel."""

    # Financial model: AWS compute vCPU-hr ($0.136/hr on c6g.xlarge), electricity ($0.12/kWh), and carbon liability ($0.085/kg)
    COMPUTE_HOURLY_USD = 0.136
    ELECTRICITY_KWH_USD = 0.12
    COST_PER_KG_CO2E_USD = 0.085
    WEEKLY_INTEREST_RATE = 0.025  # 2.5% compounding drag on cloud OPEX

    # Algorithmic complexity runtime & resource profiles per 1,000 invocations
    PATTERN_PROFILES: Dict[str, Dict[str, float]] = {
        "NESTED_LOOPS_DEPTH_3+": {"duration_1k_s": 1.85, "cpu_pct": 92.0, "mem_mb": 256.0},
        "NESTED_LOOPS": {"duration_1k_s": 1.85, "cpu_pct": 92.0, "mem_mb": 256.0},
        "UNCACHED_NETWORK_IN_LOOP": {"duration_1k_s": 2.10, "cpu_pct": 65.0, "mem_mb": 384.0},
        "N_PLUS_ONE_QUERY_IN_LOOP": {"duration_1k_s": 1.75, "cpu_pct": 72.0, "mem_mb": 512.0},
        "RAW_DB_CURSOR_NO_CONTEXT": {"duration_1k_s": 0.90, "cpu_pct": 55.0, "mem_mb": 320.0},
        "QUADRATIC_STRING_CONCAT_IN_LOOP": {"duration_1k_s": 0.55, "cpu_pct": 74.0, "mem_mb": 512.0},
        "HIDDEN_ITERATIVE_COMPUTATION": {"duration_1k_s": 1.15, "cpu_pct": 84.0, "mem_mb": 512.0},
        "INEFFICIENT_REGEX_IN_LOOP": {"duration_1k_s": 0.65, "cpu_pct": 80.0, "mem_mb": 192.0},
        "THREAD_THRASHING_IN_LOOP": {"duration_1k_s": 1.40, "cpu_pct": 88.0, "mem_mb": 640.0},
        "SYNC_FILE_IO_IN_LOOP": {"duration_1k_s": 1.25, "cpu_pct": 58.0, "mem_mb": 256.0},
        "SLEEP_IN_LOOP": {"duration_1k_s": 1.50, "cpu_pct": 35.0, "mem_mb": 128.0},
        "JSON_SERIALIZE_IN_LOOP": {"duration_1k_s": 0.60, "cpu_pct": 76.0, "mem_mb": 384.0},
        "SORTED_IN_LOOP": {"duration_1k_s": 0.75, "cpu_pct": 82.0, "mem_mb": 256.0},
        "RECURSION_WITHOUT_MEMOIZATION": {"duration_1k_s": 1.60, "cpu_pct": 94.0, "mem_mb": 512.0},
        "LINEAR_LOOKUP_IN_LOOP": {"duration_1k_s": 0.48, "cpu_pct": 70.0, "mem_mb": 160.0},
        "EXCESSIVE_LOGGING_IN_LOOP": {"duration_1k_s": 0.38, "cpu_pct": 50.0, "mem_mb": 128.0},
        "PANDAS_ITERROWS_IN_LOOP": {"duration_1k_s": 1.45, "cpu_pct": 86.0, "mem_mb": 512.0},
        # AI / ML Carbon Waste Profiles (PyTorch / TensorFlow / LLM inference)
        "ML_CPU_ONLY_TENSOR_OPS": {"duration_1k_s": 2.40, "cpu_pct": 95.0, "mem_mb": 1024.0},
        "ML_DATALOADER_SINGLE_WORKER": {"duration_1k_s": 1.60, "cpu_pct": 68.0, "mem_mb": 768.0},
        "ML_GRAD_ENABLED_INFERENCE": {"duration_1k_s": 1.95, "cpu_pct": 90.0, "mem_mb": 1536.0},
        "ML_MISSING_INFERENCE_MODE": {"duration_1k_s": 1.20, "cpu_pct": 82.0, "mem_mb": 1024.0},
        "ML_FP32_NO_AMP": {"duration_1k_s": 2.20, "cpu_pct": 94.0, "mem_mb": 2048.0},
        "ML_EPOCH_CHECKPOINT_SPAM": {"duration_1k_s": 1.35, "cpu_pct": 62.0, "mem_mb": 1024.0},
        "ML_REDUNDANT_MODEL_RELOAD": {"duration_1k_s": 2.80, "cpu_pct": 88.0, "mem_mb": 2048.0},
        "ML_UNBOUNDED_TOKEN_GENERATION": {"duration_1k_s": 2.50, "cpu_pct": 92.0, "mem_mb": 1536.0},
    }

    SEVERITY_FALLBACK_PROFILES: Dict[str, Dict[str, float]] = {
        "CRITICAL": {"duration_1k_s": 1.65, "cpu_pct": 90.0, "mem_mb": 512.0},
        "HIGH": {"duration_1k_s": 0.82, "cpu_pct": 78.0, "mem_mb": 256.0},
        "MEDIUM": {"duration_1k_s": 0.36, "cpu_pct": 62.0, "mem_mb": 128.0},
        "LOW": {"duration_1k_s": 0.14, "cpu_pct": 45.0, "mem_mb": 64.0},
    }

    def __init__(self):
        self._team_debts: Dict[str, TeamEnergyDebt] = {}

    @classmethod
    def estimate_violation_impact(
        cls,
        violation: Dict[str, Any],
        daily_invocations: int = 100_000,
        carbon_intensity_gco2_kwh: float = 380.0,
    ) -> Dict[str, float]:
        """Compute annual energy (kWh), carbon (kg CO2e), and cost (USD) for a single violation using CalibratedEnergyModel."""
        from app.calibrated_energy import CalibratedEnergyModel

        vtype = str(violation.get("violation_type", ""))
        sev = str(violation.get("severity", "MEDIUM")).upper()

        profile = cls.PATTERN_PROFILES.get(
            vtype,
            cls.SEVERITY_FALLBACK_PROFILES.get(sev, cls.SEVERITY_FALLBACK_PROFILES["MEDIUM"]),
        )

        line_start = int(violation.get("line_number") or 1)
        line_end = int(violation.get("end_line_number") or line_start)
        span_lines = max(1, line_end - line_start + 1)
        span_factor = 1.0 + min(0.6, (span_lines - 1) * 0.05)

        deduction = violation.get("deduction")
        deduction_factor = max(0.6, float(deduction) / 10.0) if deduction is not None else 1.0

        duration_1k_s = profile["duration_1k_s"] * span_factor * deduction_factor
        energy_1k = CalibratedEnergyModel.calculate_energy(
            duration_seconds=duration_1k_s,
            cpu_utilization_pct=profile["cpu_pct"],
            memory_mb=profile["mem_mb"],
        )

        joules_per_1k = float(energy_1k.energy_joules)
        annual_1k_batches = (max(1, daily_invocations) * 365.0) / 1000.0
        annual_joules = joules_per_1k * annual_1k_batches
        annual_kwh = annual_joules / 3_600_000.0
        annual_co2_kg = (annual_kwh * carbon_intensity_gco2_kwh) / 1000.0

        annual_compute_hours = (duration_1k_s * annual_1k_batches) / 3600.0
        annual_cost_usd = (
            (annual_compute_hours * cls.COMPUTE_HOURLY_USD)
            + (annual_kwh * cls.ELECTRICITY_KWH_USD)
            + (annual_co2_kg * cls.COST_PER_KG_CO2E_USD)
        )

        return {
            "joules_per_1k_calls": round(joules_per_1k, 4),
            "annual_kwh": round(annual_kwh, 3),
            "co2_kg": round(annual_co2_kg, 2),
            "cost_usd": round(annual_cost_usd, 2),
        }

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
            impact = self.estimate_violation_impact(v)
            total_kg += impact["co2_kg"]
            total_usd += impact["cost_usd"]
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
            pass  # no-op  # no-op

        return debt

    @staticmethod
    def _row_to_team_debt(row: Any) -> TeamEnergyDebt:
        patterns = json.loads(row.details_json) if row.details_json else []
        return TeamEnergyDebt(
            team_id=row.team_id,
            team_name=row.team_id,
            total_violations_count=int(row.total_violations_count or 0),
            energy_debt_kg_co2e=float(row.energy_debt_kg_co2e or 0.0),
            energy_debt_usd=float(row.energy_debt_usd or 0.0),
            weekly_interest_usd=float(row.weekly_interest_usd or 0.0),
            debt_velocity_trend=str(row.debt_velocity_trend or "STABLE"),
            top_offending_patterns=patterns,
            last_updated=row.last_updated_at.isoformat() if row.last_updated_at else datetime.now(timezone.utc).isoformat(),
        )

    def get_team_debt(self, team_id: str) -> Optional[TeamEnergyDebt]:
        if team_id in self._team_debts:
            return self._team_debts[team_id]
        try:
            from app.database import EnergyDebtLedger, SessionLocal, init_db
            init_db()
            db = SessionLocal()
            try:
                row = db.query(EnergyDebtLedger).filter(EnergyDebtLedger.team_id == team_id).first()
                if row:
                    debt = self._row_to_team_debt(row)
                    self._team_debts[team_id] = debt
                    return debt
            finally:
                db.close()
        except Exception:
            pass  # no-op
        return None

    def list_all_debts(self) -> List[TeamEnergyDebt]:
        if self._team_debts:
            return list(self._team_debts.values())
        try:
            from app.database import EnergyDebtLedger, SessionLocal, init_db
            init_db()
            db = SessionLocal()
            try:
                rows = db.query(EnergyDebtLedger).all()
                for row in rows:
                    if row.team_id not in self._team_debts:
                        self._team_debts[row.team_id] = self._row_to_team_debt(row)
            finally:
                db.close()
        except Exception:
            pass  # no-op
        return list(self._team_debts.values())


# Global singleton instance
energy_debt_tracker = EnergyDebtTracker()


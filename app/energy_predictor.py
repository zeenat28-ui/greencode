"""Pre-Production Green Deploy Predictor & Pull Request Quality Gate.

Predicts the energy, carbon, and financial cloud infrastructure delta of incoming
code changes BEFORE they are merged into production branches.

Features:
- Diffs base branch vs incoming PR audit metrics.
- Estimates percentage increase/decrease in cloud energy consumption.
- Determines whether to Pass, Warn, or Hard-Block the deployment quality gate.
- Generates clear, actionable GitHub/GitLab PR feedback summaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class DeployPredictionResult:
    """Pre-deploy energy prediction verdict for a Pull Request or deployment candidate."""
    pr_identifier: str
    decision: str  # "PASS", "WARN", "BLOCK"
    energy_delta_percent: float
    annual_cost_delta_usd: float
    annual_carbon_delta_kg: float
    baseline_score: float
    incoming_score: float
    new_violations_introduced: int
    resolved_violations: int
    recommendation_summary: str
    timestamp: str


class GreenDeployPredictor:
    """Predictive Energy Quality Gatekeeper for CI/CD backed by CalibratedEnergyModel."""

    # Default tolerance gates
    WARN_THRESHOLD_PCT = 10.0   # >10% energy regression triggers a warning
    BLOCK_THRESHOLD_PCT = 25.0  # >25% energy regression hard-blocks merge

    @classmethod
    def _audit_energy_profile(cls, audit_data: Dict[str, Any], daily_invocations: int = 100_000) -> Dict[str, float]:
        """Compute per-1k-call Joules and annualized USD/CO2e from an audit payload using CalibratedEnergyModel."""
        from app.calibrated_energy import CalibratedEnergyModel
        from app.energy_debt import EnergyDebtTracker

        # Base idle/clean execution profile per 1,000 requests (0.5s total CPU time @ 35% utilization, 256MB RAM)
        baseline_model = CalibratedEnergyModel.calculate_energy(
            duration_seconds=0.50,
            cpu_utilization_pct=35.0,
            memory_mb=256.0,
        )
        base_joules_1k = float(baseline_model.energy_joules)

        score = float(audit_data.get("green_score", 100.0))
        violations = audit_data.get("violations", [])

        # Sum physics-calibrated waste across all detected AST violations
        viol_joules_1k = 0.0
        viol_cost_usd = 0.0
        viol_co2_kg = 0.0
        for v in violations:
            impact = EnergyDebtTracker.estimate_violation_impact(v, daily_invocations=daily_invocations)
            viol_joules_1k += impact["joules_per_1k_calls"]
            viol_cost_usd += impact["cost_usd"]
            viol_co2_kg += impact["co2_kg"]

        # Account for structural score difference when raw violations list is abbreviated
        unmodeled_score_gap = max(0.0, 100.0 - score)
        score_overhead_joules_1k = unmodeled_score_gap * 0.45

        if "total_energy_joules" in audit_data and float(audit_data["total_energy_joules"]) > 0:
            total_joules_1k = float(audit_data["total_energy_joules"]) * 1000.0
        else:
            total_joules_1k = base_joules_1k + viol_joules_1k + score_overhead_joules_1k

        annual_1k_batches = (max(1, daily_invocations) * 365.0) / 1000.0
        annual_kwh = (total_joules_1k * annual_1k_batches) / 3_600_000.0
        annual_co2_kg = viol_co2_kg + ((score_overhead_joules_1k * annual_1k_batches) / 3_600_000.0) * 0.380
        annual_cost_usd = viol_cost_usd + (annual_kwh * EnergyDebtTracker.ELECTRICITY_KWH_USD)

        return {
            "joules_1k": total_joules_1k,
            "annual_cost_usd": annual_cost_usd,
            "annual_co2_kg": annual_co2_kg,
        }

    @classmethod
    def predict_pr_impact(
        cls,
        pr_identifier: str,
        base_audit: Dict[str, Any],
        incoming_audit: Dict[str, Any],
        block_threshold_pct: Optional[float] = None,
        warn_threshold_pct: Optional[float] = None,
    ) -> DeployPredictionResult:
        """Analyze PR diff and output definitive deployment gating verdict."""
        warn_limit = warn_threshold_pct or cls.WARN_THRESHOLD_PCT
        block_limit = block_threshold_pct or cls.BLOCK_THRESHOLD_PCT

        base_score = float(base_audit.get("green_score", 100.0))
        incoming_score = float(incoming_audit.get("green_score", 100.0))

        base_viols = base_audit.get("violations", [])
        incoming_viols = incoming_audit.get("violations", [])

        base_profile = cls._audit_energy_profile(base_audit)
        incoming_profile = cls._audit_energy_profile(incoming_audit)

        if base_profile["joules_1k"] > 0:
            energy_delta_pct = (
                (incoming_profile["joules_1k"] - base_profile["joules_1k"]) / base_profile["joules_1k"]
            ) * 100.0
        else:
            energy_delta_pct = 0.0

        energy_delta_pct = max(-100.0, energy_delta_pct)
        cost_delta_usd = incoming_profile["annual_cost_usd"] - base_profile["annual_cost_usd"]
        carbon_delta_kg = incoming_profile["annual_co2_kg"] - base_profile["annual_co2_kg"]

        # Track violation delta
        new_introduced = max(0, len(incoming_viols) - len(base_viols))
        resolved = max(0, len(base_viols) - len(incoming_viols))

        if energy_delta_pct >= block_limit or incoming_score < 70.0:
            decision = "BLOCK"
            rec = (
                f"MERGE BLOCKED: Incoming changes introduce a +{energy_delta_pct:.1f}% energy regression "
                f"(Score dropped from {base_score:.1f} to {incoming_score:.1f}). "
                f"Estimated annual cloud cost penalty: +${abs(cost_delta_usd):.2f}/yr."
            )
        elif energy_delta_pct >= warn_limit:
            decision = "WARN"
            rec = (
                f"CAUTION: Incoming changes increase energy by +{energy_delta_pct:.1f}%. "
                f"Consider refactoring high-deduction loops before shipping to production."
            )
        else:
            decision = "PASS"
            if energy_delta_pct < 0:
                rec = (
                    f"APPROVED: Clean pull request! Energy efficiency improved by {abs(energy_delta_pct):.1f}% "
                    f"(Estimated savings: ${abs(cost_delta_usd):.2f}/yr & {abs(carbon_delta_kg):.1f} kg CO2e)."
                )
            else:
                rec = "APPROVED: Pull request satisfies all Green Computing quality gates."

        return DeployPredictionResult(
            pr_identifier=pr_identifier,
            decision=decision,
            energy_delta_percent=round(energy_delta_pct, 2),
            annual_cost_delta_usd=round(cost_delta_usd, 2),
            annual_carbon_delta_kg=round(carbon_delta_kg, 2),
            baseline_score=round(base_score, 1),
            incoming_score=round(incoming_score, 1),
            new_violations_introduced=new_introduced,
            resolved_violations=resolved,
            recommendation_summary=rec,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


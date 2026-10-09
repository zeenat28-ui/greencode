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
    """Predictive Energy Quality Gatekeeper for CI/CD."""

    # Default tolerance gates
    WARN_THRESHOLD_PCT = 10.0   # >10% energy regression triggers a warning
    BLOCK_THRESHOLD_PCT = 25.0  # >25% energy regression hard-blocks merge

    # Enterprise financial coefficients
    ANNUAL_COST_PER_ENERGY_PCT = 1800.0  # ~$1,800/yr per 1% overall microservice efficiency delta
    ANNUAL_CO2_PER_ENERGY_PCT = 4200.0   # ~4.2 tons CO2e per 1% efficiency delta

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

        # Energy consumption scales inversely with green score
        # Lower score = higher energy waste
        if base_score > 0:
            score_drop_pct = ((base_score - incoming_score) / base_score) * 100.0
        else:
            score_drop_pct = 0.0

        energy_delta_pct = max(-100.0, score_drop_pct * 1.5)

        cost_delta_usd = (energy_delta_pct / 100.0) * cls.ANNUAL_COST_PER_ENERGY_PCT
        carbon_delta_kg = (energy_delta_pct / 100.0) * cls.ANNUAL_CO2_PER_ENERGY_PCT

        # Track violation delta
        new_introduced = max(0, len(incoming_viols) - len(base_viols))
        resolved = max(0, len(base_viols) - len(incoming_viols))

        if energy_delta_pct >= block_limit or incoming_score < 70.0:
            decision = "BLOCK"
            rec = (
                f"MERGE BLOCKED: Incoming changes introduce a +{energy_delta_pct:.1f}% energy regression "
                f"(Score dropped from {base_score:.1f} to {incoming_score:.1f}). "
                f"Estimated annual cloud cost penalty: +${abs(cost_delta_usd):.0f}/yr."
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
                    f"(Estimated savings: ${abs(cost_delta_usd):.0f}/yr & {abs(carbon_delta_kg):.0f} kg CO2e)."
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


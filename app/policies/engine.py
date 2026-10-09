"""Declarative Energy Policy Evaluation Engine."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class PolicyEngine:
    """Evaluates deployment rules against policy definitions."""

    @classmethod
    def evaluate(
        cls,
        policy: Dict[str, Any],
        current_energy: float,
        baseline_energy: float,
        team_budget_consumed: float = 0.0,
        team_budget_total: float = 500.0,
        grid_intensity: float = 380.0,
    ) -> Dict[str, Any]:
        safe_base = max(baseline_energy, 1e-6)
        regression_pct = round(((current_energy - safe_base) / safe_base) * 100.0, 2)
        budget_pct = round((team_budget_consumed / max(team_budget_total, 1e-6)) * 100.0, 2)

        violations: List[str] = []
        warnings: List[str] = []
        decision = "PASS"

        max_reg = policy.get("max_regression_pct", 25.0)
        if regression_pct > max_reg:
            violations.append(
                f"Deployment energy regression +{regression_pct:.1f}% exceeds threshold ({max_reg}%)"
            )
            decision = "BLOCK"

        breach_pct = policy.get("breach_threshold_pct", 100.0)
        warn_pct = policy.get("warning_threshold_pct", 70.0)
        if budget_pct >= breach_pct:
            violations.append(
                f"Team carbon budget is breached ({budget_pct:.1f}% consumed, limit is {breach_pct}%)"
            )
            decision = "BLOCK"
        elif budget_pct >= warn_pct:
            warnings.append(
                f"Team carbon budget warning ({budget_pct:.1f}% consumed, warning threshold is {warn_pct}%)"
            )
            if decision != "BLOCK":
                decision = "WARN"

        dirty_grid = policy.get("dirty_grid_threshold_gco2e", 450.0)
        if grid_intensity > dirty_grid:
            warnings.append(
                f"Regional grid carbon intensity {grid_intensity:.1f} gCO2e/kWh exceeds clean threshold ({dirty_grid})"
            )
            if decision != "BLOCK":
                decision = "WARN"

        return {
            "decision": decision,
            "is_blocked": decision == "BLOCK",
            "regression_pct": regression_pct,
            "team_budget_consumed_pct": budget_pct,
            "grid_intensity": grid_intensity,
            "violations": violations,
            "warnings": warnings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


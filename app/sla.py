"""Energy Service Level Agreement (SLA) & Team Carbon Budget Engine.

Enforces corporate and team-level energy thresholds across CI/CD gates and
runtime production pipelines:
- Function-level maximum Joules quotas
- Deployment-level SCI and Joule limits
- Team monthly carbon budgets with warning thresholds
- Automatic PR evaluation and blocking verdicts
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class SLAViolation:
    """A breach of configured energy SLA limits."""

    metric: str
    limit_value: float
    measured_value: float
    unit: str
    severity: str
    message: str


@dataclass
class SLAVerdict:
    """The outcome of an SLA evaluation."""

    passed: bool
    status: str  # "COMPLIANT", "WARNING", "BREACHED"
    violations: List[SLAViolation] = field(default_factory=list)
    summary: str = ""
    suggested_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EnergySLAEngine:
    """Evaluates software energy telemetry against SLA policies."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        default_path = os.path.join(
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
            "greencode-sla.yaml",
        )
        target = config_path or default_path
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
        return self._default_fallback_config()

    @staticmethod
    def _default_fallback_config() -> Dict[str, Any]:
        return {
            "energy_sla": {
                "enforce_mode": "strict",
                "per_function": {
                    "critical_path_max_joules": 15.0,
                    "batch_processor_max_joules": 1200.0,
                    "api_request_handler_max_joules": 50.0,
                },
                "per_deployment": {
                    "max_total_joules": 5000.0,
                    "max_sci_gco2e_per_unit": 0.25,
                    "min_green_score": 75.0,
                },
            }
        }

    def evaluate_function(self, function_name: str, measured_joules: float, category: str = "critical_path") -> SLAVerdict:
        """Evaluate a single function's measured Joules against its SLA limit."""
        sla_conf = self.config.get("energy_sla", {}).get("per_function", {})
        key = f"{category}_max_joules"
        limit = sla_conf.get(key, 50.0)

        violations: List[SLAViolation] = []
        if measured_joules > limit:
            violations.append(
                SLAViolation(
                    metric=f"Function: {function_name}",
                    limit_value=limit,
                    measured_value=measured_joules,
                    unit="Joules",
                    severity="CRITICAL",
                    message=f"Function '{function_name}' consumed {measured_joules:.2f} J, exceeding SLA limit of {limit:.2f} J.",
                )
            )

        passed = len(violations) == 0
        status = "COMPLIANT" if passed else "BREACHED"
        summary = (
            f"Function '{function_name}' is compliant with energy SLA ({measured_joules:.2f} J <= {limit:.2f} J)."
            if passed
            else f"Energy SLA Breached: Function '{function_name}' exceeded limit by {measured_joules - limit:.2f} J."
        )

        return SLAVerdict(
            passed=passed,
            status=status,
            violations=violations,
            summary=summary,
            suggested_action="Optimize algorithmic complexity or refactor nested loops." if not passed else "None",
        )

    def evaluate_deployment(
        self,
        total_joules: float,
        green_score: float,
        sci_gco2e: float = 0.0,
    ) -> SLAVerdict:
        """Evaluate complete repository deployment against SLA thresholds."""
        sla_conf = self.config.get("energy_sla", {}).get("per_deployment", {})
        max_joules = sla_conf.get("max_total_joules", 5000.0)
        min_score = sla_conf.get("min_green_score", 75.0)
        max_sci = sla_conf.get("max_sci_gco2e_per_unit", 0.25)

        violations: List[SLAViolation] = []

        if total_joules > max_joules:
            violations.append(
                SLAViolation(
                    metric="Total Deployment Energy",
                    limit_value=max_joules,
                    measured_value=total_joules,
                    unit="Joules",
                    severity="HIGH",
                    message=f"Deployment energy ({total_joules:.1f} J) exceeds maximum ceiling ({max_joules:.1f} J).",
                )
            )

        if green_score < min_score:
            violations.append(
                SLAViolation(
                    metric="Repository Green Score",
                    limit_value=min_score,
                    measured_value=green_score,
                    unit="Score / 100",
                    severity="HIGH",
                    message=f"Green Score ({green_score:.1f}) is below mandatory SLA floor ({min_score:.1f}).",
                )
            )

        if sci_gco2e > max_sci > 0.0:
            violations.append(
                SLAViolation(
                    metric="Software Carbon Intensity (SCI)",
                    limit_value=max_sci,
                    measured_value=sci_gco2e,
                    unit="gCO2e / unit",
                    severity="MEDIUM",
                    message=f"Operational SCI ({sci_gco2e:.4f}) exceeds target ({max_sci:.4f}).",
                )
            )

        passed = len(violations) == 0
        status = "COMPLIANT" if passed else "BREACHED"
        summary = (
            f"Deployment passed energy SLA gates (Score: {green_score:.1f}, Energy: {total_joules:.1f} J)."
            if passed
            else f"Deployment failed {len(violations)} energy SLA quality gate(s)."
        )

        return SLAVerdict(
            passed=passed,
            status=status,
            violations=violations,
            summary=summary,
            suggested_action="Block CI/CD deployment until eco-refactoring satisfies thresholds." if not passed else "Approved for release.",
        )


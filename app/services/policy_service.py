"""Enterprise Energy Policy Service.

Evaluates deployment energy regression limits, team carbon budget thresholds (70%/90%/100%),
and grid carbon conditions to issue binding gatekeeper decisions.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from app.audit_logs import AuditLogManager
from app.database import EnergyPolicy, SessionLocal

logger = logging.getLogger("greencode.services.policy_service")


class PolicyService:
    """Service for managing declarative policies and evaluating deployment compliance."""

    @classmethod
    def get_policy(cls, org_id: int, project_id: Optional[int] = None) -> Dict[str, Any]:
        """Fetch active policy for org/project or return enterprise defaults."""
        db: Session = SessionLocal()
        try:
            query = db.query(EnergyPolicy).filter(EnergyPolicy.org_id == org_id)
            if project_id:
                query = query.filter(EnergyPolicy.project_id == project_id)
            policy = query.first()

            if not policy:
                return {
                    "org_id": org_id,
                    "project_id": project_id,
                    "name": "Default Enterprise Policy",
                    "max_regression_pct": 25.0,
                    "max_energy_per_run_joules": 1.0,
                    "max_sci_score": 80.0,
                    "warning_threshold_pct": 70.0,
                    "critical_threshold_pct": 90.0,
                    "breach_threshold_pct": 100.0,
                    "auto_block_deploy": True,
                    "auto_rollback_k8s": True,
                    "dirty_grid_threshold_gco2e": 450.0,
                }

            return {
                "id": policy.id,
                "org_id": policy.org_id,
                "project_id": policy.project_id,
                "team_id": policy.team_id,
                "name": policy.name,
                "max_regression_pct": policy.max_regression_pct,
                "max_energy_per_run_joules": policy.max_energy_per_run_joules,
                "max_sci_score": policy.max_sci_score,
                "warning_threshold_pct": policy.warning_threshold_pct,
                "critical_threshold_pct": policy.critical_threshold_pct,
                "breach_threshold_pct": policy.breach_threshold_pct,
                "auto_block_deploy": policy.auto_block_deploy,
                "auto_rollback_k8s": policy.auto_rollback_k8s,
                "dirty_grid_threshold_gco2e": policy.dirty_grid_threshold_gco2e,
            }
        finally:
            db.close()

    @classmethod
    def save_policy(
        cls,
        org_id: int,
        policy_data: Dict[str, Any],
        project_id: Optional[int] = None,
        actor: str = "org_admin",
    ) -> Dict[str, Any]:
        """Save or update enterprise energy policies."""
        db: Session = SessionLocal()
        try:
            query = db.query(EnergyPolicy).filter(EnergyPolicy.org_id == org_id)
            if project_id:
                query = query.filter(EnergyPolicy.project_id == project_id)
            policy = query.first()

            if not policy:
                policy = EnergyPolicy(
                    org_id=org_id,
                    project_id=project_id,
                    name=policy_data.get("name", "Custom Policy"),
                )
                db.add(policy)

            policy.max_regression_pct = float(policy_data.get("max_regression_pct", 25.0))
            policy.max_energy_per_run_joules = float(policy_data.get("max_energy_per_run_joules", 1.0))
            policy.max_sci_score = float(policy_data.get("max_sci_score", 80.0))
            policy.warning_threshold_pct = float(policy_data.get("warning_threshold_pct", 70.0))
            policy.critical_threshold_pct = float(policy_data.get("critical_threshold_pct", 90.0))
            policy.breach_threshold_pct = float(policy_data.get("breach_threshold_pct", 100.0))
            policy.auto_block_deploy = bool(policy_data.get("auto_block_deploy", True))
            policy.auto_rollback_k8s = bool(policy_data.get("auto_rollback_k8s", True))
            policy.dirty_grid_threshold_gco2e = float(policy_data.get("dirty_grid_threshold_gco2e", 450.0))

            db.commit()
            db.refresh(policy)

            # Record audit trail
            AuditLogManager.record_event(
                org_id=org_id,
                action="policy:save",
                resource_type="energy_policy",
                resource_id=str(policy.id),
                status="SUCCESS",
                details=policy_data,
                actor=actor,
            )

            return cls.get_policy(org_id, project_id)
        finally:
            db.close()

    @classmethod
    def evaluate_deployment_rules(
        cls,
        org_id: int,
        current_energy: float,
        baseline_energy: float,
        team_budget_consumed: float = 0.0,
        team_budget_total: float = 500.0,
        grid_intensity: float = 380.0,
        project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Core product logic: Evaluate rules to pass, warn, or block deployment."""
        policy = cls.get_policy(org_id, project_id)
        safe_base = max(baseline_energy, 1e-6)
        regression_pct = round(((current_energy - safe_base) / safe_base) * 100.0, 2)
        budget_pct = round((team_budget_consumed / max(team_budget_total, 1e-6)) * 100.0, 2)

        violations = []
        warnings = []
        decision = "PASS"

        # Rule 1: Deployment energy regression threshold (>25% blocks)
        if regression_pct > policy["max_regression_pct"]:
            violations.append(
                f"Deployment energy regression +{regression_pct:.1f}% exceeds maximum allowable threshold ({policy['max_regression_pct']}%)"
            )
            decision = "BLOCK"

        # Rule 2 & 3: Team carbon budget consumption thresholds
        if budget_pct >= policy["breach_threshold_pct"]:
            violations.append(
                f"Team carbon budget is breached ({budget_pct:.1f}% consumed, limit is {policy['breach_threshold_pct']}%)"
            )
            decision = "BLOCK"
        elif budget_pct >= policy["warning_threshold_pct"]:
            warnings.append(
                f"Team carbon budget warning ({budget_pct:.1f}% consumed, warning threshold is {policy['warning_threshold_pct']}%)"
            )
            if decision != "BLOCK":
                decision = "WARN"

        # Rule 4: Dirty grid carbon intensity window
        if grid_intensity > policy["dirty_grid_threshold_gco2e"]:
            warnings.append(
                f"Regional grid carbon intensity {grid_intensity:.1f} gCO2e/kWh exceeds clean threshold ({policy['dirty_grid_threshold_gco2e']})"
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
            "policy_applied": policy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


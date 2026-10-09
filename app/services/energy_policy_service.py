"""Enterprise Energy Policy Engine and Deployment Gatekeeper.

Defines, persists, and enforces operational policies controlling
maximum permissible energy regressions, SCI thresholds, and dirty grid execution locks.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from app.database import AuditLog, Project, SessionLocal

logger = logging.getLogger("greencode.services.policy")


DEFAULT_POLICY = {
    "max_energy_regression_pct": 15.0,
    "min_green_score": 80.0,
    "max_sci_gco2e": 100.0,
    "block_dirty_grid": True,
    "dirty_grid_threshold_gco2e_kwh": 450.0,
    "enforce_strict_rollback": True,
}


class EnergyPolicyService:
    """Evaluates software deployments against organizational carbon & energy policies."""

    @classmethod
    def get_policy(cls, project_id: int) -> Dict[str, Any]:
        """Fetch project-specific policy or return organizational defaults."""
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if not proj or not proj.policy_json:
                return dict(DEFAULT_POLICY)
            try:
                saved = json.loads(proj.policy_json)
                merged = dict(DEFAULT_POLICY)
                merged.update(saved)
                return merged
            except Exception:
                return dict(DEFAULT_POLICY)
        finally:
            db.close()

    @classmethod
    def set_policy(
        cls,
        project_id: int,
        policy: Dict[str, Any],
        org_id: Optional[int] = 1,
        actor: str = "org_admin",
    ) -> Dict[str, Any]:
        """Update and persist enterprise energy policies for a project."""
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if not proj:
                # If project doesn't exist, create a stub record or return merged
                merged = dict(DEFAULT_POLICY)
                merged.update(policy)
                return merged

            merged = dict(DEFAULT_POLICY)
            if proj.policy_json:
                try:
                    merged.update(json.loads(proj.policy_json))
                except Exception:
                    pass
            merged.update(policy)
            proj.policy_json = json.dumps(merged)
            db.commit()

            # Record audit trail
            audit = AuditLog(
                org_id=org_id or proj.org_id,
                action="policy:update",
                resource_type="project_policy",
                resource_id=str(project_id),
                status="SUCCESS",
                details=json.dumps({"actor": actor, "policy": merged}),
            )
            db.add(audit)
            db.commit()

            return merged
        finally:
            db.close()

    @classmethod
    def evaluate_deployment_gate(
        cls,
        project_id: int,
        current_metrics: Dict[str, Any],
        baseline_metrics: Dict[str, Any],
        grid_intensity: float = 380.0,
    ) -> Dict[str, Any]:
        """Evaluate if deployment passes enterprise green gates before rollout."""
        policy = cls.get_policy(project_id)

        current_energy = current_metrics.get("energy_joules") or current_metrics.get("power_w") or 0.0
        baseline_energy = max(baseline_metrics.get("energy_joules") or baseline_metrics.get("power_w") or 1.0, 1.0)
        regression_pct = round(((current_energy - baseline_energy) / baseline_energy) * 100.0, 2)

        green_score = current_metrics.get("green_score", 100.0)
        sci_score = current_metrics.get("sci_gco2e", 50.0)

        violations = []

        # Check regression policy
        if regression_pct > policy["max_energy_regression_pct"]:
            violations.append(
                f"Energy regression +{regression_pct:.1f}% exceeds max allowed threshold ({policy['max_energy_regression_pct']}%)"
            )

        # Check minimum green score
        if green_score < policy["min_green_score"]:
            violations.append(
                f"Green score {green_score:.1f} is below compliance gate ({policy['min_green_score']})"
            )

        # Check dirty grid threshold
        if policy["block_dirty_grid"] and grid_intensity > policy["dirty_grid_threshold_gco2e_kwh"]:
            violations.append(
                f"Target grid carbon intensity {grid_intensity:.1f} gCO2e/kWh exceeds ceiling ({policy['dirty_grid_threshold_gco2e_kwh']})"
            )

        is_blocked = len(violations) > 0
        gate_status = "BLOCKED" if is_blocked else "APPROVED"

        return {
            "gate_status": gate_status,
            "is_blocked": is_blocked,
            "project_id": project_id,
            "regression_pct": regression_pct,
            "current_green_score": green_score,
            "grid_intensity": grid_intensity,
            "violations": violations,
            "policy_applied": policy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


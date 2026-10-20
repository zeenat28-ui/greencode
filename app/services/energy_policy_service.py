"""Enterprise Energy Policy Engine and Deployment Gatekeeper.

Defines, persists, and enforces operational policies controlling
maximum permissible energy regressions, SCI thresholds, and dirty grid execution locks.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from app.database import AuditLog, Base, Project, SessionLocal, sync_engine

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
        Base.metadata.create_all(bind=sync_engine)
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
    def get_project_org_id(cls, project_id: int) -> Optional[int]:
        """Return the organisation that owns a project, or ``None`` if unknown.

        Used by routers to enforce the tenant boundary against the *authoritative*
        project organisation instead of trusting a client-supplied ``org_id``.
        """
        Base.metadata.create_all(bind=sync_engine)
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            if not proj:
                return None
            return int(proj.org_id or 0) or None
        except Exception:
            return None
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
        Base.metadata.create_all(bind=sync_engine)
        db: Session = SessionLocal()
        try:
            proj = db.query(Project).filter(Project.id == project_id).first()
            merged = dict(DEFAULT_POLICY)
            if not proj:
                merged.update(policy)
                proj = Project(
                    id=project_id,
                    org_id=org_id or 1,
                    name=f"Project-{project_id}",
                    slug=f"project-{project_id}",
                    policy_json=json.dumps(merged),
                )
                db.add(proj)
                db.commit()
                target_org_id = org_id or 1
            else:
                if proj.policy_json:
                    try:
                        merged.update(json.loads(proj.policy_json))
                    except Exception:
                        pass  # no-op
                merged.update(policy)
                proj.policy_json = json.dumps(merged)
                db.commit()
                target_org_id = org_id or proj.org_id
        finally:
            db.close()

        from app.audit_logs import AuditLogManager
        AuditLogManager.record_event(
            org_id=target_org_id,
            action="policy:update",
            resource_type="project_policy",
            resource_id=str(project_id),
            status="SUCCESS",
            details={"actor": actor, "policy": merged},
            actor=actor,
        )
        return merged

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

        # Check maximum SCI threshold
        if sci_score is not None and float(sci_score) > float(policy.get("max_sci_gco2e", 100.0)):
            violations.append(
                f"SCI score {float(sci_score):.2f} gCO2e exceeds max allowed ceiling ({policy['max_sci_gco2e']} gCO2e)"
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
            "current_sci_gco2e": sci_score,
            "grid_intensity": grid_intensity,
            "violations": violations,
            "policy_applied": policy,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


"""Enterprise Kubernetes Rollback Orchestration Service.

Evaluates live cluster power and carbon metrics against baseline profiles,
determines energy regression thresholds, and executes automated Kubernetes
rollbacks while maintaining an immutable audit log.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session
from app.database import AuditLog, SessionLocal
from app.kubernetes_profiler import trigger_kubernetes_rollback

logger = logging.getLogger("greencode.services.rollback")


class RollbackService:
    """Automated and policy-driven Kubernetes deployment rollback controller."""

    CRITICAL_SPIKE_THRESHOLD_PCT = 35.0
    WARNING_SPIKE_THRESHOLD_PCT = 20.0

    @classmethod
    def evaluate_and_rollback(
        cls,
        namespace: str,
        deployment_name: str,
        current_power_w: float,
        baseline_power_w: float,
        org_id: Optional[int] = 1,
        auto_trigger: bool = True,
        actor: str = "greencode-sentinel",
    ) -> Dict[str, Any]:
        """Evaluate deployment power spike against baseline and execute rollback if critical."""
        baseline_safe = max(baseline_power_w, 1.0)
        spike_pct = round(((current_power_w - baseline_safe) / baseline_safe) * 100.0, 2)

        rollback_triggered = False
        rollback_status: Dict[str, Any] = {}
        verdict = "HEALTHY"

        if spike_pct >= cls.CRITICAL_SPIKE_THRESHOLD_PCT:
            verdict = "CRITICAL_SPIKE"
            if auto_trigger:
                rollback_status = trigger_kubernetes_rollback(
                    namespace=namespace,
                    deployment_name=deployment_name,
                )
                rollback_triggered = rollback_status.get("status") in ("SUCCESS", "LOCAL_EMULATION")
        elif spike_pct >= cls.WARNING_SPIKE_THRESHOLD_PCT:
            verdict = "WARNING_REGRESSION"

        # Record audit event
        db: Session = SessionLocal()
        try:
            audit = AuditLog(
                org_id=org_id,
                action="k8s:rollback_evaluation",
                resource_type="k8s_deployment",
                resource_id=f"{namespace}/{deployment_name}",
                status="ROLLBACK_TRIGGERED" if rollback_triggered else verdict,
                details=json.dumps({
                    "current_power_w": current_power_w,
                    "baseline_power_w": baseline_power_w,
                    "spike_pct": spike_pct,
                    "verdict": verdict,
                    "auto_trigger": auto_trigger,
                    "actor": actor,
                    "rollback_status": rollback_status,
                }),
            )
            db.add(audit)
            db.commit()
        finally:
            db.close()

        return {
            "deployment": f"{namespace}/{deployment_name}",
            "current_power_w": current_power_w,
            "baseline_power_w": baseline_power_w,
            "spike_pct": spike_pct,
            "verdict": verdict,
            "rollback_triggered": rollback_triggered,
            "rollback_status": rollback_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def execute_manual_rollback(
        cls,
        namespace: str,
        deployment_name: str,
        org_id: Optional[int] = 1,
        actor: str = "org_admin",
        reason: str = "Manual energy budget violation override",
    ) -> Dict[str, Any]:
        """Manually trigger an emergency rollback via authorized operator."""
        status = trigger_kubernetes_rollback(
            namespace=namespace,
            deployment_name=deployment_name,
        )

        db: Session = SessionLocal()
        try:
            audit = AuditLog(
                org_id=org_id,
                action="k8s:manual_rollback",
                resource_type="k8s_deployment",
                resource_id=f"{namespace}/{deployment_name}",
                status=status.get("status", "EXECUTED"),
                details=json.dumps({
                    "actor": actor,
                    "reason": reason,
                    "dispatch": status,
                }),
            )
            db.add(audit)
            db.commit()
        finally:
            db.close()

        return {
            "deployment": f"{namespace}/{deployment_name}",
            "actor": actor,
            "reason": reason,
            "result": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


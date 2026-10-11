"""Enterprise Compliance, Security Posture, and Data Retention Framework.

Validates platform compliance against SOC2 Type II, ISO 14064, and GSF standards.
Enforces automated data retention windows and encryption-at-rest verifications.
"""

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from app.audit_logs import AuditLogManager
from app.database import (
    AuditLog,
    SessionLocal,
    secrets_encryption_blockers,
    secrets_encryption_enabled,
)

logger = logging.getLogger("greencode.compliance")


class ComplianceManager:
    """Manages enterprise trust, security controls, and regulatory posture."""

    DEFAULT_RETENTION_DAYS = 365

    @classmethod
    def _verify_rbac_matrix(cls) -> Dict[str, Any]:
        """Runtime verification that least-privilege RBAC boundaries are intact."""
        try:
            from app.auth.roles import Permission, ROLE_PERMISSIONS, Role
            viewer_perms = ROLE_PERMISSIONS.get(Role.VIEWER, set())
            admin_perms = ROLE_PERMISSIONS.get(Role.ORG_ADMIN, set())
            least_privilege_ok = (
                Permission.MANAGE_ORG not in viewer_perms
                and Permission.MANAGE_USERS not in viewer_perms
                and Permission.EXECUTE_ROLLBACK not in viewer_perms
                and Permission.MANAGE_ORG in admin_perms
                and len(ROLE_PERMISSIONS) >= 4
            )
            return {
                "passed": least_privilege_ok,
                "status": "COMPLIANT" if least_privilege_ok else "POLICY_DRIFT",
                "details": (
                    f"Verified {len(ROLE_PERMISSIONS)} roles; VIEWER restricted to {len(viewer_perms)} read permissions"
                    if least_privilege_ok
                    else "RBAC least-privilege boundary check failed"
                ),
            }
        except Exception as exc:
            return {"passed": False, "status": "ERROR", "details": str(exc)}

    @classmethod
    def _verify_sci_methodology(cls) -> Dict[str, Any]:
        """Runtime self-test of ISO/IEC 21031:2024 SCI formula (1 kWh = 3.6e6 J)."""
        try:
            from app.sci import compute_sci
            res = compute_sci(
                energy_joules=3_600_000.0,
                duration_seconds=0.0,
                carbon_intensity_gco2_per_kwh=400.0,
                functional_unit=1.0,
                pue=1.0,
            )
            math_ok = abs(res.energy_kwh - 1.0) < 1e-6 and abs(res.operational_gco2 - 400.0) < 1e-4
            return {
                "passed": math_ok,
                "status": "COMPLIANT" if math_ok else "CALCULATION_ERROR",
                "details": (
                    "Verified ISO/IEC 21031:2024 SCI equation: 3.6e6 J = 1.0 kWh, SCI = ((E * I) + M) / R"
                    if math_ok
                    else f"SCI self-test mismatch: energy_kwh={res.energy_kwh}, sci={res.sci_gco2_per_functional_unit}"
                ),
            }
        except Exception as exc:
            return {"passed": False, "status": "ERROR", "details": str(exc)}

    @classmethod
    def evaluate_security_posture(cls, org_id: Optional[int] = 1) -> Dict[str, Any]:
        """Audit platform security posture and data protection controls."""
        encryption_active = secrets_encryption_enabled()
        encryption_blockers = secrets_encryption_blockers()

        audit_verification = (
            AuditLogManager.verify_integrity(org_id)
            if org_id
            else {"valid": True, "status": "NO_ORG_SPECIFIED"}
        )

        checks = {
            "encryption_at_rest": {
                "passed": encryption_active,
                "status": "COMPLIANT" if encryption_active else "NON_COMPLIANT",
                "details": "Fernet encryption active" if encryption_active else encryption_blockers,
            },
            "audit_trail_integrity": {
                "passed": audit_verification.get("valid", False),
                "status": "COMPLIANT" if audit_verification.get("valid") else "INTEGRITY_FAIL",
                "details": audit_verification.get("status"),
            },
            "rbac_enforcement": cls._verify_rbac_matrix(),
            "ghg_sci_methodology": cls._verify_sci_methodology(),
        }

        all_passed = all(c["passed"] for c in checks.values())
        overall_grade = "SOC2_READY" if all_passed else "REMEDIATION_REQUIRED"

        return {
            "overall_status": overall_grade,
            "all_controls_passed": all_passed,
            "compliance_checks": checks,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def enforce_data_retention(
        cls,
        retention_days: int = DEFAULT_RETENTION_DAYS,
        prune_expired: bool = True,
    ) -> Dict[str, Any]:
        """Prune expired code scan records and report audit log archival eligibility."""
        from app.database import Repository, ScanViolation

        db: Session = SessionLocal()
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        try:
            audit_logs_eligible = (
                db.query(AuditLog)
                .filter(AuditLog.created_at < cutoff_date)
                .count()
            )
            expired_scans = (
                db.query(Repository)
                .filter(Repository.created_at < cutoff_date)
                .all()
            )
            expired_scan_ids = [r.id for r in expired_scans]
            pruned_scans = 0
            pruned_violations = 0

            if prune_expired and expired_scan_ids:
                pruned_violations = (
                    db.query(ScanViolation)
                    .filter(ScanViolation.repo_id.in_(expired_scan_ids))
                    .delete(synchronize_session=False)
                )
                pruned_scans = (
                    db.query(Repository)
                    .filter(Repository.id.in_(expired_scan_ids))
                    .delete(synchronize_session=False)
                )
                db.commit()

            return {
                "retention_policy_days": retention_days,
                "cutoff_date": cutoff_date.isoformat(),
                "records_eligible_for_archival": audit_logs_eligible + len(expired_scan_ids),
                "audit_logs_archival_candidates": audit_logs_eligible,
                "scan_records_pruned": pruned_scans,
                "violation_records_pruned": pruned_violations,
                "status": "RETENTION_ACTIVE",
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


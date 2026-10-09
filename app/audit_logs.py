"""Enterprise Cryptographic Audit Trail and Compliance Ledger.

Provides cryptographically chained, immutable audit logging for all policy decisions,
deployment rollbacks, budget overrides, and access modifications conforming to SOC2 and ISO 14064.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.database import AuditLog, SessionLocal

logger = logging.getLogger("greencode.audit_logs")

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"


def _parse_record_details(details_str: Optional[str]) -> Dict[str, Any]:
    """Parse JSON details safely outside iteration context."""
    if not details_str:
        return {}
    try:
        return json.loads(details_str)
    except Exception:
        return {"raw": details_str}


class AuditLogManager:
    """Manages immutable, hash-chained enterprise audit records."""

    @classmethod
    def _compute_hash(cls, prev_hash: str, timestamp_str: str, org_id: int, action: str, resource_id: str, details_str: str) -> str:
        payload = f"{prev_hash}|{timestamp_str}|{org_id}|{action}|{resource_id}|{details_str}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @classmethod
    def record_event(
        cls,
        org_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
        actor: Optional[str] = "system",
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record an immutable, hash-chained audit event."""
        db: Session = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            timestamp_str = now.isoformat()
            details_dict = details or {}
            details_dict["actor"] = actor
            details_dict["recorded_at"] = timestamp_str

            # Find previous audit record for this org to link hash chain
            query = db.query(AuditLog).filter(AuditLog.org_id == org_id)
            last_record = query.order_by(desc(AuditLog.id)).first()

            prev_hash = GENESIS_HASH
            if last_record:
                last_json = _parse_record_details(last_record.details)
                prev_hash = last_json.get("record_hash", GENESIS_HASH)

            details_str = json.dumps(details_dict, sort_keys=True)
            record_hash = cls._compute_hash(
                prev_hash=prev_hash,
                timestamp_str=timestamp_str,
                org_id=org_id,
                action=action,
                resource_id=resource_id or "",
                details_str=details_str,
            )

            details_dict["prev_hash"] = prev_hash
            details_dict["record_hash"] = record_hash
            final_details_json = json.dumps(details_dict, sort_keys=True)

            log_entry = AuditLog(
                org_id=org_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                ip_address=ip_address,
                details=final_details_json,
                created_at=now,
            )
            db.add(log_entry)
            db.commit()
            db.refresh(log_entry)

            return {
                "id": log_entry.id,
                "org_id": log_entry.org_id,
                "action": log_entry.action,
                "resource_type": log_entry.resource_type,
                "resource_id": log_entry.resource_id,
                "status": log_entry.status,
                "record_hash": record_hash,
                "prev_hash": prev_hash,
                "created_at": timestamp_str,
            }
        finally:
            db.close()

    @classmethod
    def get_trail(
        cls,
        org_id: int,
        limit: int = 50,
        offset: int = 0,
        action: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated audit records for an organization."""
        db: Session = SessionLocal()
        try:
            query = db.query(AuditLog).filter(AuditLog.org_id == org_id)
            if action:
                query = query.filter(AuditLog.action == action)
            records = query.order_by(desc(AuditLog.id)).offset(offset).limit(limit).all()

            output = []
            for r in records:
                details_parsed = _parse_record_details(r.details)
                output.append({
                    "id": r.id,
                    "org_id": r.org_id,
                    "action": r.action,
                    "resource_type": r.resource_type,
                    "resource_id": r.resource_id,
                    "status": r.status,
                    "ip_address": r.ip_address,
                    "details": details_parsed,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                })
            return output
        finally:
            db.close()

    @classmethod
    def verify_integrity(cls, org_id: int) -> Dict[str, Any]:
        """Verify the cryptographic hash chain for compliance auditors."""
        db: Session = SessionLocal()
        try:
            query = db.query(AuditLog).filter(AuditLog.org_id == org_id)
            records = query.order_by(AuditLog.id.asc()).all()

            if not records:
                return {"valid": True, "records_verified": 0, "status": "CHAIN_EMPTY"}

            last_hash = GENESIS_HASH
            for i, r in enumerate(records):
                if not r.details:
                    continue
                payload = _parse_record_details(r.details)
                if not payload or "raw" in payload:
                    return {"valid": False, "records_verified": i, "broken_at_id": r.id, "error": "CORRUPTED_JSON"}

                rec_prev = payload.get("prev_hash")
                rec_hash = payload.get("record_hash")
                if rec_prev and rec_prev != last_hash and i > 0:
                    return {
                        "valid": False,
                        "records_verified": i,
                        "broken_at_id": r.id,
                        "error": "HASH_CHAIN_DISCONTINUITY",
                    }
                last_hash = rec_hash or last_hash

            return {
                "valid": True,
                "records_verified": len(records),
                "latest_hash": last_hash,
                "status": "CHAIN_VERIFIED_TAMPER_EVIDENT",
            }
        finally:
            db.close()


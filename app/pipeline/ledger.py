"""Hash-chained evidence ledger for the verification pipeline.

A carbon claim that cannot be audited afterwards is a press release. Every
verdict the pipeline issues is appended to a ledger where each entry commits to
its predecessor:

    entry_hash = SHA256(seq | prev_hash | canonical_json(entry_body))

Editing or deleting any historical entry invalidates every hash after it, and
`verify_chain` reports the first broken link with its sequence number. That is
the property the pipeline actually promises: the record of what was decided, and
of what evidence was in hand at the time, cannot be quietly rewritten later.

The chain lives in the existing SQLAlchemy session factory rather than a new
storage engine, so it inherits the project's connection pooling, WAL pragmas and
transaction retry behaviour for free.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text, desc, select

from app.database import Base, SessionLocal, init_db

GENESIS_HASH = "0" * 64

# Canonical fields hashed into the chain. Anything not in this list (received_at,
# row ids, delivery receipts) is transport metadata and is excluded on purpose so
# that re-delivering the same evidence cannot produce a different hash.
_CHAINED_FIELDS = (
    "event_id",
    "event_type",
    "severity",
    "repo",
    "claim_id",
    "verdict",
    "confidence",
    "summary",
    "evidence_json",
)


class PipelineLedgerEntry(Base):
    """One immutable decision record in the verification chain."""

    __tablename__ = "pipeline_ledger"

    id = Column(Integer, primary_key=True, index=True)
    seq = Column(Integer, unique=True, index=True, nullable=False)
    event_id = Column(String(128), index=True, nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    repo = Column(String(255), nullable=True, index=True)
    claim_id = Column(String(128), nullable=True, index=True)

    severity = Column(String(16), default="INFO", nullable=False, index=True)
    verdict = Column(String(32), default="RECORDED", nullable=False, index=True)
    confidence = Column(Float, default=0.0)

    summary = Column(Text, nullable=True)
    evidence_json = Column(Text, nullable=True)

    prev_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), nullable=False)
    signature_verified = Column(Boolean, default=False, nullable=False)
    notified = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


@dataclass
class ChainLink:
    """A single (entry, prev_hash) pair used while verifying the chain."""

    seq: int
    payload: Dict[str, Any]
    prev_hash: str
    entry_hash: str


@dataclass
class ChainReport:
    """Result of a full chain re-verification."""

    ok: bool
    checked: int = 0
    broken_at_seq: Optional[int] = None
    reason: str = ""
    head_hash: str = GENESIS_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checked": self.checked,
            "broken_at_seq": self.broken_at_seq,
            "reason": self.reason,
            "head_hash": self.head_hash,
        }


def _entry_payload(row: PipelineLedgerEntry) -> Dict[str, Any]:
    """Rebuild the hashed payload from a persisted row."""
    evidence = None
    if row.evidence_json:
        try:
            evidence = json.loads(row.evidence_json)
        except (TypeError, ValueError):
            evidence = {"_unparsable": row.evidence_json[:200]}
    return {
        "event_id": row.event_id,
        "event_type": row.event_type,
        "severity": row.severity,
        "repo": row.repo,
        "claim_id": row.claim_id,
        "verdict": row.verdict,
        "confidence": row.confidence,
        "summary": row.summary,
        "evidence_json": evidence,
    }


def head() -> Tuple[int, str]:
    """Return `(next_seq, prev_hash)` for a new append.

    Called inside the append lock so two concurrent webhooks cannot both read the
    same tail and fork the chain - which would produce two "heads" and make the
    chain permanently unverifiable.
    """
    init_db()
    db = SessionLocal()
    try:
        row = (
            db.query(PipelineLedgerEntry)
            .order_by(desc(PipelineLedgerEntry.seq))
            .first()
        )
        if row is None:
            return 1, GENESIS_HASH
        return int(row.seq) + 1, row.entry_hash
    finally:
        db.close()


def append(
    *,
    event_id: str,
    event_type: str,
    severity: str = "INFO",
    repo: Optional[str] = None,
    claim_id: Optional[str] = None,
    verdict: str = "RECORDED",
    confidence: float = 0.0,
    summary: str = "",
    evidence: Optional[Dict[str, Any]] = None,
    signature_verified: bool = False,
) -> Dict[str, Any]:
    """Append one entry to the chain and return the persisted record.

    Raises `ValueError` when `event_id` has already been recorded: the pipeline
    is idempotent by design, and a duplicate delivery is a retry, not a second
    decision.
    """
    init_db()
    with _APPEND_LOCK:
        db = SessionLocal()
        try:
            duplicate = (
                db.query(PipelineLedgerEntry)
                .filter(PipelineLedgerEntry.event_id == event_id)
                .first()
            )
        finally:
            db.close()
        if duplicate is not None:
            raise ValueError(f"event_id '{event_id}' is already in the ledger")

        seq, prev_hash = head()
        payload = {
            "event_id": event_id,
            "event_type": event_type,
            "severity": severity,
            "repo": repo,
            "claim_id": claim_id,
            "verdict": verdict,
            "confidence": float(confidence),
            "summary": summary,
            "evidence_json": evidence or {},
        }
        entry_hash = compute_entry_hash(seq, prev_hash, payload)

        db = SessionLocal()
        try:
            row = PipelineLedgerEntry(
                seq=seq,
                evidence_json=json.dumps(evidence or {}, default=str),
                prev_hash=prev_hash,
                entry_hash=entry_hash,
                signature_verified=signature_verified,
                **{k: v for k, v in payload.items() if k != "evidence_json"},
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return _row_to_dict(row)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def _row_to_dict(row: PipelineLedgerEntry) -> Dict[str, Any]:
    """Serialise a ledger row for API responses and CLI output."""
    evidence: Optional[Dict[str, Any]] = None
    if row.evidence_json:
        try:
            evidence = json.loads(row.evidence_json)
        except (TypeError, ValueError):
            evidence = None
    return {
        "seq": row.seq,
        "event_id": row.event_id,
        "event_type": row.event_type,
        "repo": row.repo,
        "claim_id": row.claim_id,
        "severity": row.severity,
        "verdict": row.verdict,
        "confidence": row.confidence,
        "summary": row.summary,
        "evidence": evidence,
        "prev_hash": row.prev_hash,
        "entry_hash": row.entry_hash,
        "signature_verified": bool(row.signature_verified),
        "notified": bool(row.notified),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def verify_chain() -> ChainReport:
    """Re-verify the entire ledger from genesis.

    Walks entries in sequence order, recomputing each hash and checking that it
    matches both the stored digest and the previous entry's digest. A mismatch
    pinpoints the first tampered or deleted record.
    """
    init_db()
    db = SessionLocal()
    try:
        rows = db.query(PipelineLedgerEntry).order_by(PipelineLedgerEntry.seq.asc()).all()
    finally:
        db.close()

    prev_hash = GENESIS_HASH
    checked = 0
    for row in rows:
        payload = _entry_payload(row)
        recomputed = compute_entry_hash(row.seq, prev_hash, payload)
        if recomputed != row.entry_hash:
            return ChainReport(
                ok=False,
                checked=checked,
                broken_at_seq=row.seq,
                reason="entry_hash_mismatch",
                head_hash=prev_hash,
            )
        if row.prev_hash != prev_hash:
            return ChainReport(
                ok=False,
                checked=checked,
                broken_at_seq=row.seq,
                reason="prev_hash_mismatch",
                head_hash=prev_hash,
            )
        prev_hash = row.entry_hash
        checked += 1

    return ChainReport(ok=True, checked=checked, head_hash=prev_hash)


def recent(
    limit: int = 25,
    repo: Optional[str] = None,
    verdict: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Newest-first page of ledger entries, optionally filtered."""
    init_db()
    limit = max(1, min(int(limit), 200))
    db = SessionLocal()
    try:
        query = db.query(PipelineLedgerEntry)
        if repo:
            query = query.filter(PipelineLedgerEntry.repo == repo)
        if verdict:
            query = query.filter(PipelineLedgerEntry.verdict == verdict)
        rows = (
            query.order_by(desc(PipelineLedgerEntry.seq))
            .limit(limit)
            .all()
        )
        return [_row_to_dict(r) for r in rows]
    finally:
        db.close()


def find_by_event_id(event_id: str) -> Optional[Dict[str, Any]]:
    """Look up a single entry by its idempotency key."""
    init_db()
    db = SessionLocal()
    try:
        row = (
            db.query(PipelineLedgerEntry)
            .filter(PipelineLedgerEntry.event_id == event_id)
            .first()
        )
        return _row_to_dict(row) if row else None
    finally:
        db.close()


def mark_notified(seq: int) -> bool:
    """Record that operator notifications for an entry were dispatched."""
    init_db()
    db = SessionLocal()
    try:
        row = db.query(PipelineLedgerEntry).filter(PipelineLedgerEntry.seq == seq).first()
        if row is None:
            return False
        row.notified = True
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


_APPEND_LOCK = threading.Lock()


def canonical_body(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Project an entry down to exactly the fields the chain commits to."""
    return {key: entry.get(key) for key in _CHAINED_FIELDS}


def compute_entry_hash(seq: int, prev_hash: str, entry: Dict[str, Any]) -> str:
    """Hash one ledger entry, chaining it onto `prev_hash`.

    `sort_keys` and fixed separators make the digest independent of dict
    insertion order, so the same entry hashes identically across processes and
    Python versions.
    """
    material = json.dumps(
        canonical_body(entry), sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(f"{seq}|{prev_hash}|{material}".encode("utf-8")).hexdigest()

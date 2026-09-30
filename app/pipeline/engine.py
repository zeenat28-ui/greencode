"""Pipeline orchestrator: file a claim, file evidence, get a verdict.

This is the module the HTTP layer and the n8n webhook call. It owns the two
lifecycle questions the rest of the codebase does not:

1. **Idempotency.** CI retries, n8n replays and duplicate webhooks are normal
   traffic, not attacks. A repeated `event_id` returns the original record with
   `duplicate: true` instead of appending a second, contradictory ledger entry.
2. **Custody.** Evidence is held in memory for fast verification, and the
   *decisions* are persisted to the hash chain. The claim/evidence window is
   intentionally bounded and dropped oldest-first, so a long-running process
   cannot be used to grow the heap without limit. Decisions - the part that must
   survive a restart - are durable; raw samples are a verification input, not the
   system of record.
"""

from __future__ import annotations

import logging
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.pipeline import ledger
from app.pipeline.config import PipelineConfig
from app.pipeline.notifier import notify
from app.pipeline.signing import SignatureResult, verify_signature
from app.pipeline.verifier import (
    Claim,
    ClaimError,
    Evidence,
    Verdict,
    VERDICT_INVALID,
    verify,
)

logger = logging.getLogger("greencode.pipeline")

# Bounds on the in-memory correlation window. Claims beyond this are dropped
# oldest-first; their verdicts remain in the ledger forever.
MAX_TRACKED_CLAIMS = 500
MAX_EVIDENCE_PER_CLAIM = 200

_LOCK = threading.RLock()
_CLAIMS: "OrderedDict[str, Claim]" = OrderedDict()
_EVIDENCE: Dict[str, List[Evidence]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _remember_claim(claim: Claim) -> None:
    _CLAIMS[claim.claim_id] = claim
    _CLAIMS.move_to_end(claim.claim_id)
    _EVIDENCE.setdefault(claim.claim_id, [])
    while len(_CLAIMS) > MAX_TRACKED_CLAIMS:
        evicted, _ = _CLAIMS.popitem(last=False)
        _EVIDENCE.pop(evicted, None)


def _remember_evidence(item: Evidence) -> None:
    bucket = _EVIDENCE.setdefault(item.claim_id, [])
    # Dedupe by evidence_id: the same physical run can be delivered by both a CI
    # retry and an n8n replay, and counting it twice would halve the apparent
    # run-to-run spread and inflate confidence.
    if any(e.evidence_id == item.evidence_id for e in bucket):
        return
    bucket.append(item)
    if len(bucket) > MAX_EVIDENCE_PER_CLAIM:
        del bucket[: len(bucket) - MAX_EVIDENCE_PER_CLAIM]


def new_event_id(prefix: str = "evt") -> str:
    """Generate a unique, sortable-enough idempotency key."""
    return f"{prefix}_{uuid.uuid4().hex}"


def authenticate(
    body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
    cfg: Optional[PipelineConfig] = None,
) -> SignatureResult:
    """Authenticate an inbound evidence POST.

    Development with no secret configured accepts unsigned payloads, and says so
    in the result, so the endpoint can label the ledger entry as unverified
    rather than silently treating it as trustworthy.
    """
    cfg = cfg or PipelineConfig.from_env()
    if not cfg.webhook_secret:
        return SignatureResult(
            ok=cfg.allow_unsigned, reason="unsigned_allowed" if cfg.allow_unsigned else "no_secret_configured"
        )
    return verify_signature(
        cfg.webhook_secret,
        body,
        signature_header,
        timestamp_header,
        max_skew_seconds=cfg.max_skew_seconds,
    )


def file_claim(
    claim: Claim,
    *,
    cfg: Optional[PipelineConfig] = None,
    record: bool = True,
) -> Dict[str, Any]:
    """Register a prediction and record it in the ledger."""
    cfg = cfg or PipelineConfig.from_env()
    with _LOCK:
        _remember_claim(claim)
    entry: Optional[Dict[str, Any]] = None
    if record:
        entry = ledger.append(
            event_id=new_event_id("claim"),
            event_type="claim_filed",
            severity="INFO",
            repo=claim.repo,
            claim_id=claim.claim_id,
            verdict="CLAIM_OPEN",
            confidence=0.0,
            summary=(
                f"Claimed {claim.predicted_reduction_pct:.2f}% energy reduction on "
                f"{claim.repo} (source: {claim.source})."
            ),
            evidence=claim.to_dict(),
        )
    return {"claim": claim.to_dict(), "ledger_entry": entry}



def file_evidence(
    item: Evidence,
    *,
    event_id: Optional[str] = None,
    signature_verified: bool = False,
    cfg: Optional[PipelineConfig] = None,
    should_notify: bool = True,
) -> Dict[str, Any]:
    """Accept a measurement, re-verify the claim, record and notify.

    Returns the verdict plus the ledger receipt. An `event_id` already present in
    the ledger short-circuits the whole flow, which is what makes an at-least-
    once delivery channel safe to point at this endpoint.
    """
    cfg = cfg or PipelineConfig.from_env()
    eid = event_id or new_event_id("ev")

    existing = ledger.find_by_event_id(eid)
    if existing is not None:
        return {
            "duplicate": True,
            "event_id": eid,
            "ledger_entry": existing,
            "verdict": existing.get("verdict"),
        }

    with _LOCK:
        claim = _CLAIMS.get(item.claim_id)
        _remember_evidence(item)
        bucket = list(_EVIDENCE.get(item.claim_id, []))

    if claim is None:
        # Evidence for an unknown claim is a real operational signal, not an
        # error to swallow: it usually means the runner filed before the claim
        # arrived, or a claim_id is misspelled somewhere upstream.
        entry = ledger.append(
            event_id=eid,
            event_type="evidence_orphaned",
            severity="MEDIUM",
            claim_id=item.claim_id,
            verdict=VERDICT_INVALID,
            confidence=0.0,
            summary=(
                f"Evidence '{item.evidence_id}' references unknown claim "
                f"'{item.claim_id}'; it was recorded but not verified."
            ),
            evidence=item.to_dict(),
            signature_verified=signature_verified,
        )
        return {
            "duplicate": False,
            "event_id": eid,
            "verdict": VERDICT_INVALID,
            "ledger_entry": entry,
            "error": "unknown_claim",
        }



    verdict = verify(claim, bucket, config=cfg)

    entry = ledger.append(
        event_id=eid,
        event_type="evidence_filed",
        severity=verdict.severity,
        repo=claim.repo,
        claim_id=claim.claim_id,
        verdict=verdict.verdict,
        confidence=verdict.confidence,
        summary=" ".join(verdict.reasons[:2])[:500],
        evidence={
            "evidence": item.to_dict(),
            "observed_reduction_pct": verdict.observed_reduction_pct,
            "evidence_count": verdict.evidence_count,
            "hardware_evidence_count": verdict.hardware_evidence_count,
        },
        signature_verified=signature_verified,
    )

    delivery: List[Dict[str, Any]] = []
    if should_notify and entry is not None:
        delivery = notify(verdict, cfg)
        if any(d.get("delivered") for d in delivery):
            ledger.mark_notified(entry["seq"])

    return {
        "duplicate": False,
        "event_id": eid,
        "verdict": verdict.verdict,
        "ledger_entry": entry,
        "notification": delivery,
        "result": verdict.to_dict(),
    }


def check_claim(claim_id: str, *, cfg: Optional[PipelineConfig] = None) -> Optional[Verdict]:
    """Re-evaluate a claim against everything filed so far, without recording."""
    cfg = cfg or PipelineConfig.from_env()
    with _LOCK:
        claim = _CLAIMS.get(claim_id)
        bucket = list(_EVIDENCE.get(claim_id, []))
    if claim is None:
        return None
    return verify(claim, bucket, config=cfg)


def get_claim(claim_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        claim = _CLAIMS.get(claim_id)
    return claim.to_dict() if claim else None


def list_claims() -> List[Dict[str, Any]]:
    with _LOCK:
        return [c.to_dict() for c in _CLAIMS.values()]


def clear() -> None:
    """Drop all in-memory state. Used by tests; the ledger is untouched."""
    with _LOCK:
        _CLAIMS.clear()
        _EVIDENCE.clear()

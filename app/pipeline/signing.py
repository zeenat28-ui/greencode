"""HMAC request signing for pipeline evidence intake.

A verification pipeline that anyone can POST to is worse than no pipeline: it
manufactures the exact "reality" it is supposed to be checking. So evidence
intake is authenticated with a shared-secret HMAC over `timestamp + "." + body`,
the timestamp is bounded to reject replays, and every failure mode returns a
distinct reason instead of a generic 403.

The scheme is deliberately boring (HMAC-SHA256, hex digest, `X-GreenCode-
Signature: sha256=<hex>`) because the senders are CI runners, cron jobs and
n8n webhooks written in half a dozen languages, not a bespoke JS client.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

SIGNATURE_HEADER = "x-greencode-signature"
TIMESTAMP_HEADER = "x-greencode-timestamp"
SIGNATURE_PREFIX = "sha256="


@dataclass
class SignatureResult:
    """Outcome of verifying an inbound request signature."""

    ok: bool
    reason: str = ""
    timestamp: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"verified": self.ok, "reason": self.reason, "timestamp": self.timestamp}


def compute_signature(secret: str, body: bytes, timestamp: Optional[int] = None) -> Tuple[str, int]:
    """Return `(signature_header_value, timestamp)` for a request body.

    Exposed so the project's own emitters - and the test suite - produce byte
    identical signatures to third-party senders.
    """
    ts = int(timestamp if timestamp is not None else time.time())
    # A dot separator is used instead of concatenation so a body cannot be
    # shifted across the timestamp boundary (`123` + `456` vs `12` + `3456`).
    signed_payload = f"{ts}.".encode("utf-8") + (body or b"")
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"{SIGNATURE_PREFIX}{digest}", ts


def verify_signature(
    secret: str,
    body: bytes,
    signature_header: Optional[str],
    timestamp_header: Optional[str],
    *,
    max_skew_seconds: int = 300,
    now: Optional[float] = None,
) -> SignatureResult:
    """Verify a signed intake request.

    Checks, in order: timestamp parses, timestamp is inside the skew window,
    signature is present and well-formed, signature matches. Each failure is
    reported separately because "signature invalid" and "replay" call for
    completely different operator responses.
    """
    if not secret:
        return SignatureResult(ok=False, reason="no_secret_configured")

    if not timestamp_header:
        return SignatureResult(ok=False, reason="missing_timestamp")

    try:
        ts = int(str(timestamp_header).strip())
    except (TypeError, ValueError):
        return SignatureResult(ok=False, reason="malformed_timestamp")

    current = time.time() if now is None else now
    if abs(current - ts) > max(0, int(max_skew_seconds)):
        return SignatureResult(
            ok=False,
            reason="stale_timestamp",
            timestamp=ts,
        )

    if not signature_header:
        return SignatureResult(ok=False, reason="missing_signature", timestamp=ts)

    provided = str(signature_header).strip()
    if provided.startswith(SIGNATURE_PREFIX):
        provided = provided[len(SIGNATURE_PREFIX):]
    if len(provided) != 64:
        return SignatureResult(ok=False, reason="malformed_signature", timestamp=ts)

    signed_payload = f"{ts}.".encode("utf-8") + (body or b"")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, provided.lower()):
        return SignatureResult(ok=False, reason="signature_mismatch", timestamp=ts)

    return SignatureResult(ok=True, reason="ok", timestamp=ts)

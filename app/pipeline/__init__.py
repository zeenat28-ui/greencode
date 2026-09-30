"""GreenCode Reality Verification Pipeline.

Answers one question honestly: *did the optimisation actually happen in the real
world, or did we only predict it?*

GreenCode is a prediction engine - it estimates energy reductions, scores code
and projects SCI. Predictions are cheap; the expensive, honest question is what
the hardware actually did. This package closes that loop: a claim is filed, real
measurements are filed against it, and the pipeline returns a verdict with a
confidence score, a severity, the exact reasons behind it, and what is still
missing to close it.

Every decision is appended to a hash-chained ledger, so the record of what was
claimed, what was measured and what was decided cannot be quietly rewritten
afterwards. Modelled energy can never confirm a claim - only a hardware counter
reading can, mirroring the distinction `app.sci` already enforces.

Modules:
    config    - environment-driven policy and channel configuration
    signing   - HMAC authentication and replay rejection for evidence intake
    verifier  - claim/evidence comparison and verdict logic
    ledger    - tamper-evident, hash-chained decision records
    notifier  - Slack / Teams / email delivery of verdicts
    engine    - the orchestrator that wires the above together
"""

from app.pipeline.config import PipelineConfig
from app.pipeline.ledger import ChainReport, verify_chain
from app.pipeline.signing import SignatureResult, compute_signature, verify_signature
from app.pipeline.verifier import (
    VERDICT_CONTRADICTED,
    VERDICT_INVALID,
    VERDICT_PARTIAL,
    VERDICT_UNVERIFIED,
    VERDICT_VERIFIED,
    Claim,
    ClaimError,
    Evidence,
    Verdict,
    verify,
)

__all__ = [
    "PipelineConfig",
    "ChainReport",
    "verify_chain",
    "SignatureResult",
    "compute_signature",
    "verify_signature",
    "Claim",
    "ClaimError",
    "Evidence",
    "Verdict",
    "verify",
    "VERDICT_VERIFIED",
    "VERDICT_PARTIAL",
    "VERDICT_UNVERIFIED",
    "VERDICT_CONTRADICTED",
    "VERDICT_INVALID",
]

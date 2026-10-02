"""Claim verification engine: does the predicted saving show up in the real world?

GreenCode already produces *predictions* - a refactor is estimated to cut energy
by N%, a pipeline is scored, an SCI figure is projected. The gap that matters is
whether any of that survives contact with a real machine, a real workload and a
real grid. This module closes that gap by comparing a **claim** against
**evidence** and returning a verdict with an explicit confidence and an explicit
statement of what is still missing.

The design rule throughout: the engine never rounds a guess up to a fact. An
unverified claim is reported as `UNVERIFIED`, not as a smaller number that looks
confirmed. Modelled evidence can never reach `VERIFIED` - only a hardware counter
reading can, because that is the same distinction `app.sci` already enforces.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.energy_sensors import HARDWARE_METHODS as HARDWARE_METHOD_SET
from app.pipeline.config import PipelineConfig
from app.sci import carbon_equivalents, compute_sci, sci_grade

# Verdicts, ordered from "nothing proven" to "proven".
VERDICT_VERIFIED = "VERIFIED"
VERDICT_PARTIAL = "PARTIALLY_VERIFIED"
VERDICT_UNVERIFIED = "UNVERIFIED"
VERDICT_CONTRADICTED = "CONTRADICTED"
VERDICT_INVALID = "INVALID_EVIDENCE"

VERDICTS = (
    VERDICT_VERIFIED,
    VERDICT_PARTIAL,
    VERDICT_UNVERIFIED,
    VERDICT_CONTRADICTED,
    VERDICT_INVALID,
)

# Only a hardware counter counts as proof. Mirrors app.sci's measurement tiers,
# and is imported from one place so the two can never disagree about what counts
# as a measurement. `scaphandre` belongs here: it reads the same RAPL hardware,
# just over HTTP instead of sysfs, so excluding it meant a real counter reading
# could never confirm a claim.
HARDWARE_METHODS = frozenset(HARDWARE_METHOD_SET)

# Below this many samples a comparison is anecdote, not evidence.
DEFAULT_MIN_SAMPLES = 3

# Default acceptable deviation between predicted and observed reduction.
DEFAULT_TOLERANCE_PCT = 15.0

# Spread of observed values beyond this means the workload is not repeatable


class ClaimError(ValueError):
    """Raised when a claim or evidence record is structurally unusable."""


class Claim:
    """A prediction the pipeline will later hold the system to.

    Attributes:
        claim_id: Stable identifier used to correlate evidence.
        repo: ``owner/repo`` the claim belongs to.
        predicted_reduction_pct: Expected energy reduction, e.g. 45.0.
        baseline_energy_joules: Energy of the unoptimised code path.
        baseline_sci: Optional pre-refactor SCI for a like-for-like comparison.
        source: Where the claim came from (refactor, audit, CI gate).
    """

    __slots__ = (
        "claim_id",
        "repo",
        "predicted_reduction_pct",
        "baseline_energy_joules",
        "baseline_sci",
        "source",
        "zone",
        "created_at",
        "metadata",
    )

    def __init__(
        self,
        claim_id: str,
        repo: str,
        predicted_reduction_pct: float,
        *,
        baseline_energy_joules: Optional[float] = None,
        baseline_sci: Optional[float] = None,
        source: str = "refactor",
        zone: str = "US-CAL-CISO",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not claim_id or not str(claim_id).strip():
            raise ClaimError("claim_id is required to correlate evidence.")
        if not repo or not str(repo).strip():
            raise ClaimError("repo is required; a claim must name what it claims about.")
        try:
            pct = float(predicted_reduction_pct)
        except (TypeError, ValueError):
            raise ClaimError(
                f"predicted_reduction_pct must be numeric. Got {predicted_reduction_pct!r}."
            )
        if not (0.0 <= pct <= 100.0):
            raise ClaimError(f"predicted_reduction_pct must be 0-100. Got {pct}.")
        self.claim_id = str(claim_id)
        self.repo = str(repo)
        self.predicted_reduction_pct = pct
        self.baseline_energy_joules = (
            float(baseline_energy_joules) if baseline_energy_joules is not None else None
        )
        self.baseline_sci = float(baseline_sci) if baseline_sci is not None else None
        self.source = source
        self.zone = zone
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "repo": self.repo,
            "predicted_reduction_pct": self.predicted_reduction_pct,
            "baseline_energy_joules": self.baseline_energy_joules,
            "baseline_sci": self.baseline_sci,
            "source": self.source,
            "zone": self.zone,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Claim":
        return cls(
            claim_id=data.get("claim_id", ""),
            repo=data.get("repo", ""),
            predicted_reduction_pct=data.get("predicted_reduction_pct", 0.0),
            baseline_energy_joules=data.get("baseline_energy_joules"),
            baseline_sci=data.get("baseline_sci"),
            source=data.get("source", "refactor"),
            zone=data.get("zone", "US-CAL-CISO"),
            metadata=data.get("metadata") or {},
        )


class Evidence:
    """A measured observation of a workload, from a real execution."""

    __slots__ = (
        "evidence_id",
        "claim_id",
        "energy_joules",
        "duration_seconds",
        "functional_unit",
        "measurement_method",
        "carbon_intensity",
        "source",
        "observed_at",
        "metadata",
    )

    def __init__(
        self,
        evidence_id: str,
        claim_id: str,
        energy_joules: float,
        *,
        duration_seconds: float = 1.0,
        functional_unit: float = 1.0,
        measurement_method: str = "model",
        carbon_intensity: float = 380.0,
        source: str = "unknown",
        observed_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not claim_id or not str(claim_id).strip():
            raise ClaimError("claim_id is required on evidence; evidence is never free-standing.")
        try:
            joules = float(energy_joules)
        except (TypeError, ValueError):
            raise ClaimError(f"energy_joules must be numeric. Got {energy_joules!r}.")
        if joules < 0:
            raise ClaimError(f"energy_joules cannot be negative. Got {joules}.")
        if float(functional_unit) <= 0:
            raise ClaimError(
                "functional_unit (R) must be positive. An energy total with no "
                "functional unit cannot be compared against a claim."
            )
        self.evidence_id = str(evidence_id)
        self.claim_id = str(claim_id)
        self.energy_joules = joules
        self.duration_seconds = max(0.0, float(duration_seconds))
        self.functional_unit = float(functional_unit)
        self.measurement_method = str(measurement_method)
        self.carbon_intensity = float(carbon_intensity)
        self.source = source
        self.observed_at = observed_at or datetime.now(timezone.utc).isoformat()
        self.metadata = metadata or {}

    @property
    def is_hardware(self) -> bool:
        """Whether this came from a real counter rather than a TDP model."""
        return self.measurement_method in HARDWARE_METHODS

    def sci(self) -> Dict[str, Any]:
        """SCI for this observation, via the shared GSF implementation."""
        return compute_sci(
            energy_joules=self.energy_joules,
            duration_seconds=self.duration_seconds,
            carbon_intensity_gco2_per_kwh=self.carbon_intensity,
            functional_unit=self.functional_unit,
            measurement_method=self.measurement_method,
        ).to_dict()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "claim_id": self.claim_id,
            "energy_joules": self.energy_joules,
            "duration_seconds": self.duration_seconds,
            "functional_unit": self.functional_unit,
            "measurement_method": self.measurement_method,
            "measurement_is_hardware": self.is_hardware,
            "carbon_intensity": self.carbon_intensity,
            "source": self.source,
            "observed_at": self.observed_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        return cls(
            evidence_id=data.get("evidence_id", ""),
            claim_id=data.get("claim_id", ""),
            energy_joules=data.get("energy_joules", 0.0),
            duration_seconds=data.get("duration_seconds", 1.0),
            functional_unit=data.get("functional_unit", 1.0),
            measurement_method=data.get("measurement_method", "model"),
            carbon_intensity=data.get("carbon_intensity", 380.0),
            source=data.get("source", "unknown"),
            observed_at=data.get("observed_at"),
            metadata=data.get("metadata") or {},
        )


@dataclass
class Verdict:
    """The pipeline's decision on a claim, plus everything needed to defend it."""

    claim_id: str
    repo: str
    verdict: str
    confidence: float
    predicted_reduction_pct: float
    observed_reduction_pct: Optional[float]
    evidence_count: int
    hardware_evidence_count: int
    measurement_is_hardware: bool
    reasons: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    observed_sci: Optional[float] = None
    baseline_sci: Optional[float] = None
    carbon_avoided_gco2e: Optional[float] = None
    carbon_equivalents: Dict[str, float] = field(default_factory=dict)
    samples: List[Dict[str, Any]] = field(default_factory=list)
    policy: Dict[str, Any] = field(default_factory=dict)
    decided_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def severity(self) -> str:
        """Operator-facing severity, derived from the verdict.

        A contradicted claim is the only genuinely urgent outcome: the platform
        published a number that reality refused to support. Everything else is
        informational.
        """
        if self.verdict == VERDICT_CONTRADICTED:
            return "HIGH"
        if self.verdict == VERDICT_INVALID:
            return "MEDIUM"
        if self.verdict == VERDICT_UNVERIFIED:
            return "LOW"
        return "INFO"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "repo": self.repo,
            "verdict": self.verdict,
            "severity": self.severity,
            "confidence": round(self.confidence, 4),
            "predicted_reduction_pct": round(self.predicted_reduction_pct, 4),
            "observed_reduction_pct": (
                None
                if self.observed_reduction_pct is None
                else round(self.observed_reduction_pct, 4)
            ),
            "evidence_count": self.evidence_count,
            "hardware_evidence_count": self.hardware_evidence_count,
            "measurement_is_hardware": self.measurement_is_hardware,
            "reasons": self.reasons,
            "gaps": self.gaps,
            "observed_sci": self.observed_sci,
            "baseline_sci": self.baseline_sci,
            "carbon_avoided_gco2e": self.carbon_avoided_gco2e,
            "carbon_equivalents": self.carbon_equivalents,
            "samples": self.samples,
            "policy": self.policy,
            "decided_at": self.decided_at,
        }


def _median(values: List[float]) -> float:
    return float(statistics.median(values))


def _spread_pct(values: List[float]) -> float:
    """Relative spread of samples, as a percentage of the median.

    Uses the median absolute deviation rather than the standard deviation
    because one wildly-off run (a noisy neighbour, a thermal-throttled CI box)
    must not be allowed to widen everyone's tolerance.
    """
    if len(values) < 2:
        return 0.0
    med = _median(values)
    if med <= 0:
        return 0.0
    mad = _median([abs(v - med) for v in values])
    # 1.4826 scales MAD to a standard-deviation equivalent for normal data.
    return (1.4826 * mad / med) * 100.0


def verify(
    claim: Claim,
    evidence: List[Evidence],
    *,
    config: Optional[PipelineConfig] = None,
    tolerance_pct: Optional[float] = None,
    min_samples: Optional[int] = None,
    max_spread_pct: Optional[float] = None,
) -> Verdict:
    """Compare a claim against its evidence and decide what is actually true.

    The checks run in a fixed order, cheapest and most disqualifying first, so
    the returned `reasons` and `gaps` always explain the verdict:

    1. No evidence             -> UNVERIFIED ("nothing measured yet").
    2. No baseline             -> UNVERIFIED (a percentage off no baseline is
                                  arithmetic, not measurement).
    3. Workload not repeatable -> PARTIALLY_VERIFIED, flagged unstable.
    4. No hardware counter     -> UNVERIFIED. A model cannot confirm a model.
    5. Observed energy rose    -> CONTRADICTED.
    6. Observed within band    -> VERIFIED.
    7. Observed short of claim -> PARTIALLY_VERIFIED or UNVERIFIED by how far.

    `confidence` is the agreement between prediction and observation, reduced for
    small sample counts, high spread and modelled inputs. It is a reporting aid,
    not a statistical guarantee.
    """
    cfg = config or PipelineConfig()
    tolerance = float(tolerance_pct if tolerance_pct is not None else cfg.default_tolerance_pct)
    min_n = int(min_samples if min_samples is not None else cfg.default_min_samples)
    spread_limit = float(
        max_spread_pct if max_spread_pct is not None else cfg.max_spread_pct
    )
    policy = {
        "tolerance_pct": tolerance,
        "min_samples": min_n,
        "max_spread_pct": spread_limit,
    }

    matching = [e for e in evidence if e.claim_id == claim.claim_id]
    hardware = [e for e in matching if e.is_hardware]

    def _base(value: str, confidence: float, reasons: List[str], gaps: List[str]) -> Verdict:
        return Verdict(
            claim_id=claim.claim_id,
            repo=claim.repo,
            verdict=value,
            confidence=max(0.0, min(1.0, confidence)),
            predicted_reduction_pct=claim.predicted_reduction_pct,
            observed_reduction_pct=None,
            evidence_count=len(matching),
            hardware_evidence_count=len(hardware),
            measurement_is_hardware=bool(hardware),
            reasons=reasons,
            gaps=gaps,
            baseline_sci=claim.baseline_sci,
            policy=policy,
        )

    # 1. Nothing measured yet.
    if not matching:
        return _base(
            VERDICT_UNVERIFIED,
            0.0,
            ["No evidence has been filed for this claim."],
            [f"File at least {min_n} measured runs via POST /api/pipeline/evidence."],
        )

    # 2. A reduction percentage is meaningless without a measured baseline.
    if claim.baseline_energy_joules is None or claim.baseline_energy_joules <= 0:
        return _base(
            VERDICT_UNVERIFIED,
            0.0,
            [
                f"{len(matching)} evidence record(s) received, but the claim carries no "
                "measured baseline_energy_joules, so no reduction can be computed."
            ],
            [
                "Re-file the claim with baseline_energy_joules captured from the "
                "unoptimised code path."
            ],
        )

    # Normalise every sample to energy per functional unit so runs of different
    # sizes stay comparable. Comparing raw joules across different workloads is
    # the single easiest way to produce a confidently wrong number.
    per_unit = [e.energy_joules / e.functional_unit for e in matching]
    median_per_unit = _median(per_unit)
    spread = _spread_pct(per_unit)
    mean_units = sum(e.functional_unit for e in matching) / len(matching)
    baseline_per_unit = claim.baseline_energy_joules / max(1.0, mean_units)
    observed_reduction = (1.0 - (median_per_unit / baseline_per_unit)) * 100.0
    delta = observed_reduction - claim.predicted_reduction_pct
    relative_delta = abs(delta) / max(1.0, abs(claim.predicted_reduction_pct))

    effective = hardware or matching
    observed_sci = _median([
        compute_sci(
            energy_joules=e.energy_joules,
            duration_seconds=e.duration_seconds,
            carbon_intensity_gco2_per_kwh=e.carbon_intensity,
            functional_unit=e.functional_unit,
            measurement_method=e.measurement_method,
        ).sci_gco2_per_functional_unit
        for e in effective
    ])
    carbon_avoided = None
    if claim.baseline_sci:
        carbon_avoided = (claim.baseline_sci - observed_sci) * _median(
            [e.functional_unit for e in effective]
        )

    samples = [
        {
            "evidence_id": e.evidence_id,
            "energy_per_functional_unit_joules": round(
                e.energy_joules / e.functional_unit, 6
            ),
            "energy_joules": e.energy_joules,
            "functional_unit": e.functional_unit,
            "duration_seconds": e.duration_seconds,
            "measurement_method": e.measurement_method,
            "measurement_is_hardware": e.is_hardware,
            "source": e.source,
            "observed_at": e.observed_at,
        }
        for e in matching
    ]

    def _finalise(
        value: str, confidence: float, reasons: List[str], gaps: List[str]
    ) -> Verdict:
        v = _base(value, confidence, reasons, gaps)
        v.observed_reduction_pct = observed_reduction
        v.observed_sci = observed_sci
        v.carbon_avoided_gco2e = carbon_avoided
        v.carbon_equivalents = carbon_equivalents(carbon_avoided) if carbon_avoided else {}
        v.samples = samples
        v.reasons = list(v.reasons) + [
            f"Observed reduction {observed_reduction:.2f}% vs predicted "
            f"{claim.predicted_reduction_pct:.2f}% across {len(matching)} sample(s) "
            f"(spread {spread:.1f}%)."
        ]
        return v

    # 5. Reality moved the wrong way: the workload now costs MORE energy.
    if observed_reduction < -tolerance:
        return _finalise(
            VERDICT_CONTRADICTED,
            0.95,
            [
                f"Observed energy is {abs(observed_reduction):.1f}% HIGHER than baseline, "
                "outside the tolerance band in either direction."
            ],
            [
                "The refactor is not delivering. Revert or re-profile before this "
                "number is published anywhere."
            ],
        )

    if not hardware:
        return _finalise(
            VERDICT_UNVERIFIED,
            0.3,
            [
                f"All {len(matching)} sample(s) came from a TDP model, not a hardware "
                "energy counter. A model can corroborate a model; it cannot confirm one."
            ],
            [
                f"Re-measure on a host exposing RAPL (/sys/class/powercap) or run on "
                f"battery, and file at least {min_n} runs with method rapl/perf/battery."
            ],
        )

    # 3. Too much run-to-run variance for a single median to be meaningful.
    if spread > spread_limit:
        return _finalise(
            VERDICT_PARTIAL,
            0.4,
            [
                f"Sample spread is {spread:.1f}%, above the {spread_limit:.1f}% "
                "repeatability limit; the workload is not stable enough to verify."
            ],
            ["Isolate the host, pin CPU frequency, and re-run a longer sample set."],
        )

    if len(matching) < min_n:
        return _finalise(
            VERDICT_PARTIAL,
            0.5,
            [
                f"Observed reduction {observed_reduction:.2f}% is consistent with the "
                f"claim, but only {len(matching)} of {min_n} required hardware samples "
                "are in hand."
            ],
            [f"File {min_n - len(matching)} more hardware-measured run(s)."],
        )

    # 6. Prediction and reality agree inside the band.
    if relative_delta * 100.0 <= tolerance:
        confidence = 1.0 - min(0.5, relative_delta * 2.0)
        confidence *= 0.7 + 0.3 * min(1.0, len(matching) / (min_n * 2.0))
        confidence *= max(0.5, 1.0 - (spread / (spread_limit * 2.0)))
        return _finalise(
            VERDICT_VERIFIED,
            confidence,
            [
                f"Hardware-measured energy fell {observed_reduction:.2f}% against a "
                f"{claim.predicted_reduction_pct:.2f}% claim "
                f"({abs(delta):.2f} points apart, tolerance {tolerance:.1f}%)."
            ],
            [],
        )

    # 7. Reality improved, but less than advertised.
    if observed_reduction > 0:
        shortfall_pct = abs(delta) / max(1.0, tolerance) * 100.0
        return _finalise(
            VERDICT_PARTIAL,
            0.55,
            [
                f"Energy did fall, by {observed_reduction:.2f}%, but that is "
                f"{abs(delta):.2f} points short of the "
                f"{claim.predicted_reduction_pct:.2f}% claimed."
            ],
            [
                "Restate the claim to the measured figure, or profile the remaining "
                "hot path before promising the original number."
            ],
        )

    return _finalise(
        VERDICT_UNVERIFIED,
        0.25,
        [
            f"Measured energy is flat to within {observed_reduction:.2f}%; the claimed "
            f"{claim.predicted_reduction_pct:.2f}% reduction did not occur."
        ],
        ["Treat the optimisation as ineffective for this workload and investigate."],
    )

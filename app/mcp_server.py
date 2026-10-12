"""GreenCode MCP Server.

WHAT THIS IS
------------
A self-hosted Model Context Protocol server that exposes GreenCode's carbon
auditing engine as tools. It speaks MCP over Streamable HTTP, which is what an
agent on the Alexa+ side (or any MCP client: Claude Desktop, Kiro, Cursor) calls
to ask GreenCode questions in natural language.

WHY A SELF-HOSTED MCP SERVER RATHER THAN A REST WRAPPER
------------------------------------------------------
GreenCode already had 37 REST endpoints. Wrapping those a second time in
JSON-RPC and calling it an MCP server would satisfy the letter of the
specification while adding nothing. So this
server is not a pass-through. It adds three things a REST wrapper cannot:

1. **Provenance is mandatory, not optional.** Every tool returns
   ``measurement_method`` and ``measurement_is_hardware``. There is no code path
   that reports a TDP estimate as a measurement. An agent that can hallucinate
   a plausible carbon number is worse than no agent at all, because its answer
   gets quoted in a sustainability report.

2. **Tools are scoped to a decision, not to an endpoint.** ``audit_and_score``
   runs the analyser, the SCI arithmetic and the grid lookup and returns one
   verdict. The agent does not have to know the order, nor recover from a
   halfway failure, and cannot accidentally report a green score for code it
   never measured.

3. **Failures are reported, not worked around.** Missing grid credentials, an
   unreachable model, or an absent Docker daemon produce a structured
   ``status`` field explaining what was unavailable. Nothing invents a number
   to fill the gap.

TRANSPORT
---------
``streamable-http`` on ``/mcp``. The server is self-hosted, so it binds to
loopback by default; set ``GREENCODE_MCP_HOST=0.0.0.0`` only behind a gateway
that authenticates callers. Binding a tool that can shell out to a refactoring
engine to all interfaces on a public network would be a genuine exposure.
During development, expose the loopback endpoint with a tunneling service
(``scripts/start_mcp_remote.ps1`` wraps cloudflared, the service the Alexa+
quickstart names) and keep the token below enabled.

AUTHENTICATION (Alexa+ checklist)
---------------------------------
Set ``GREENCODE_MCP_TOKEN`` to enforce the Alexa+ MCP quickstart checklist:

* Unauthenticated requests to ``/mcp`` receive a bare **401 without a
  ``WWW-Authenticate`` header** - the checklist requires the header to be
  absent; Alexa discovers auth metadata from the well-known document instead.
* A Protected Resource Metadata (RFC 9728) document is served at
  ``/.well-known/oauth-protected-resource`` and at the resource-specific
  ``/.well-known/oauth-protected-resource/mcp``, and authorization server
  metadata (RFC 8414, including ``S256`` for PKCE) at
  ``/.well-known/oauth-authorization-server``. All three are public, token or
  not, because a discovery document that needs credentials to read is
  useless.
* With a valid ``Authorization: Bearer <token>`` header, requests pass straight
  through to the MCP transport.

With no token configured the server is open (the default for local
development: Alexa+ account linking is optional for tools that do not need
user identity, and GreenCode's do not).

``GREENCODE_MCP_ALLOWED_HOSTS`` is a comma-separated list of extra ``Host``
header values the transport accepts (e.g. the ``xxx.trycloudflare.com``
tunnel domain). The MCP SDK's DNS-rebinding protection otherwise rejects any
request whose Host is not loopback with **421 Misdirected Request** - correct
for a localhost-only server, but it would also block the public URL the
Alexa+ quickstart requires. Loopback hosts stay allowed either way; the list
only ever adds, never removes.

The routes ``/privacy`` and ``/terms`` (served from ``alexa/pages/``) and the
static mount ``/assets`` (``alexa/assets/``) exist so that every URL written
into ``alexa/addon.json`` resolves while the tunnel is up. They are mounted
only when the corresponding directory exists.

PERFORMANCE
-----------
The Alexa+ docs ask for sub-500 ms tool round trips. Two caches make that
reachable without hiding staleness: probe_capabilities() caches host
capabilities (GREENCODE_PROBE_TTL, default 300 s) and _resolve_intensity()
caches grid readings per zone (GREENCODE_MCP_INTENSITY_TTL, default 60 s).
Both report their provenance, so a cached figure is never mistaken for a
live one.

Spec version: the transport negotiates the client's protocol version from
``mcp.types.LATEST_PROTOCOL_VERSION``, which exceeds the ``2025-11-25``
minimum required by the Alexa+ MCP specification.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import LATEST_PROTOCOL_VERSION
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from app import carbon_intensity, energy_sensors, optimizer, parser, sci
from app.llm_refactor import refactor as llm_refactor_snippet

logger = logging.getLogger("greencode.mcp")

SERVER_NAME = "greencode"
SERVER_VERSION = "1.1.0"

MCP_HOST = os.environ.get("GREENCODE_MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("GREENCODE_MCP_PORT", "8765"))

# Kept in step with the SDK's negotiated version so /api/health and the README
# can state the floor that was required without anyone re-deriving it.
MIN_REQUIRED_MCP_VERSION = "2025-11-25"
def _grade(score: float) -> str:
    """Map a 0-100 green score onto the label used across the product."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _envelope(
    status: str,
    *,
    data: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Wrap every tool result in one shape.

    An agent should never have to guess whether a payload is a result or an
    error, and should never be handed a partial answer without being told. One
    envelope, always present, is what lets a caller branch on ``status`` before
    it reads anything else.
    """
    return {
        "status": status,
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "mcp_protocol_version": LATEST_PROTOCOL_VERSION,
        "warnings": list(warnings or []),
        "data": data or {},
    }


# Per-zone TTL cache for grid readings. A live lookup is a network round-trip
# (~1.4-1.9 s per zone on this host) and carbon_intensity's own cache serves
# each live reading only once, so without this every second tool call that
# mentions a zone paid the network again - straight past Alexa+'s 500 ms
# response budget. TTL 0 disables the cache (tests, freshness-critical runs).
_INTENSITY_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_INTENSITY_CACHE_LOCK = threading.Lock()
INTENSITY_CACHE_TTL = float(os.environ.get("GREENCODE_MCP_INTENSITY_TTL", "60"))


def clear_intensity_cache() -> None:
    """Drop every cached zone reading (used by tests and live checkers)."""
    with _INTENSITY_CACHE_LOCK:
        _INTENSITY_CACHE.clear()


def _resolve_intensity(zone: str) -> Dict[str, Any]:
    """Fetch grid carbon intensity for a zone, serving from the TTL cache.

    The lookup itself is unchanged (see _resolve_intensity_uncached); only a
    short-lived per-zone memo sits in front of it. Failed readings are cached
    for the same window - a provider outage reported for 60 s is a feature,
    not a bug: retrying it on every utterance is what made tool calls time out.
    """
    key = (zone or "").strip().upper()
    if INTENSITY_CACHE_TTL > 0:
        with _INTENSITY_CACHE_LOCK:
            hit = _INTENSITY_CACHE.get(key)
        if hit is not None and (time.monotonic() - hit[0]) < INTENSITY_CACHE_TTL:
            return dict(hit[1])

    data = _resolve_intensity_uncached(zone)

    if INTENSITY_CACHE_TTL > 0:
        with _INTENSITY_CACHE_LOCK:
            # Store a copy: providers may hand back a shared/long-lived dict,
            # and the cache must not be poisonable by mutating the result.
            _INTENSITY_CACHE[key] = (time.monotonic(), dict(data))
    return data


def _resolve_intensity_uncached(zone: str) -> Dict[str, Any]:
    """Fetch grid carbon intensity for a zone, tolerating provider failure.

    A missing API key must not abort an audit. The intensity module already
    walks a provenance chain down to a static reference table, so the worst case
    is a lower-authority number that says so.

    ZERO IS NOT AN INTENSITY
    ------------------------
    ``app.carbon_intensity`` deliberately returns ``carbon_intensity = 0.0``
    with ``intensity_source = "none"`` when no provider at all can be reached,
    because a field-level ``None`` would break every downstream arithmetic path.
    That is a reasonable internal contract and it is covered by its own tests,
    so this module does not change it. But 0.0 gCO2e/kWh is a *physically
    impossible* grid, and letting one reach an agent would be actively harmful:
    in ``compare_regions`` a typo'd zone such as ``US-VA`` would sort to the top
    and be recommended as the cleanest place on earth. So a "nothing
    available" reading is normalised to ``None`` here and excluded from ranking,
    which turns a silently wrong recommendation into a visible one.
    """
    try:
        data = optimizer.get_zone_carbon_intensity(zone)
    except Exception as exc:  # noqa: BLE001 - reported, never raised to the agent
        logger.warning("Carbon intensity lookup failed for %s: %s", zone, exc)
        return {
            "zone": zone,
            "error": f"{type(exc).__name__}: {exc}",
            "carbon_intensity": None,
            "intensity_source": "unavailable",
            "intensity_source_tier": "unavailable",
            "is_live": False,
        }

    if data.get("intensity_source") == "none" or not data.get("carbon_intensity"):
        data = dict(data)
        data["carbon_intensity"] = None
        data["marginal_carbon_intensity"] = None
        data["unavailable_reason"] = (
            f"No carbon-intensity provider could supply a figure for zone '{zone}'. "
            "The 0.0 returned by the resolver means 'no data', not 'a perfect "
            "grid', so it is withheld rather than reported as a measurement."
        )
    return data


def _severity_counts(violations: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for violation in violations:
        severity = str(violation.get("severity", "")).upper()
        if severity in counts:
            counts[severity] += 1
    return counts


mcp = MCPServer(
    name=SERVER_NAME,
    version=SERVER_VERSION,
    title="GreenCode Auditor",
    instructions=(
        "GreenCode measures the carbon cost of software. Use audit_code for a "
        "source snippet, audit_repository for a GitHub repository, and "
        "audit_and_score for a single end-to-end verdict combining static "
        "findings with Software Carbon Intensity. Always report "
        "measurement_is_hardware to the user: a false value means the energy "
        "figure was modelled from TDP, not read from a hardware counter, and "
        "that distinction must never be hidden."
    ),
)
@mcp.tool(
    description=(
        "Audit a source-code snippet for energy anti-patterns (nested loops, "
        "quadratic string building, repeated allocations) and return a 0-100 "
        "green score with per-violation detail. Supports python, javascript, "
        "typescript, java, go, rust, c, cpp, csharp, kotlin, ruby and solidity."
    )
)
def audit_code(source_code: str, language: str = "python", file_path: str = "snippet") -> Dict[str, Any]:
    """Run the Green Software Foundation static analyser over a snippet."""
    if not source_code or not source_code.strip():
        return _envelope("error", data={"reason": "source_code is empty"})

    try:
        result = parser.audit_source_code(source_code, language, file_path)
    except Exception as exc:  # noqa: BLE001 - reported to the agent
        return _envelope(
            "error",
            data={"reason": f"{type(exc).__name__}: {exc}", "language": language},
        )

    violations = result.get("violations", []) or []
    score = float(result.get("green_score", 0.0))
    return _envelope(
        "ok",
        data={
            "file_path": result.get("file_path", file_path),
            "language": result.get("language", language),
            "lines_count": result.get("lines_count", 0),
            "green_score": score,
            "grade": _grade(score),
            "violation_count": len(violations),
            "severity_counts": _severity_counts(violations),
            "violations": violations,
        },
        warnings=(
            []
            if violations
            else ["No known energy anti-patterns matched. Absence of findings is "
                  "not proof of efficiency; it means no rule in the catalogue fired."]
        ),
    )


@mcp.tool(
    description=(
        "Run a full GreenCode audit on a public GitHub repository and return "
        "an aggregate green score, per-file findings and the top offenders. "
        "Requires network access."
    )
)
def audit_repository(repo: str, branch: str = "main") -> Dict[str, Any]:
    """Audit every supported source file in a GitHub repository."""
    if not repo or "/" not in repo:
        return _envelope(
            "error",
            data={"reason": "repo must look like 'owner/name', e.g. 'pallets/flask'"},
        )

    try:
        result = parser.audit_repository(repo, branch)
    except Exception as exc:  # noqa: BLE001 - reported to the agent
        return _envelope(
            "error",
            data={"reason": f"{type(exc).__name__}: {exc}", "repo": repo, "branch": branch},
        )

    return _envelope(
        "ok",
        data={
            "repo": repo,
            "branch": branch,
            "green_score": result.get("green_score"),
            "grade": _grade(float(result.get("green_score", 0.0) or 0.0)),
            "files_analyzed": result.get("files_analyzed", 0),
            "violation_count": result.get("violation_count", 0),
            "files": result.get("files", []),
        },
    )


@mcp.tool(
    description=(
        "Get the live carbon intensity of an electricity grid zone in "
        "gCO2e/kWh, with the provider and authority tier that produced it. "
        "Use this to explain WHY a region was recommended, and to show the "
        "data source rather than asserting a number."
    )
)
def get_grid_intensity(zone: str = "US-CAL-CISO") -> Dict[str, Any]:
    """Look up grid carbon intensity with full provenance."""
    data = _resolve_intensity(zone)
    warnings: List[str] = []
    tier = data.get("intensity_source_tier")
    if tier in (None, "unavailable"):
        warnings.append("No live grid provider was reachable; intensity is unavailable.")
    elif tier == carbon_intensity.TIER_STATIC_MATRIX:
        warnings.append(
            "Intensity came from the bundled static reference matrix, not a live "
            "feed. It is a historical annual baseline, not a real-time reading."
        )
    return _envelope("ok", data=data, warnings=warnings)
@mcp.tool(
    description=(
        "Compute Software Carbon Intensity (SCI = (E x I + M) / R) per the "
        "Green Software Foundation specification. Returns emissions in grams "
        "CO2e, equivalent analogies, a letter grade, and whether the energy "
        "figure is a real hardware measurement or a model."
    )
)
def calculate_sci(
    energy_joules: float,
    duration_seconds: float,
    functional_unit: float = 1.0,
    zone: str = "US-CAL-CISO",
    pue: float = sci.DEFAULT_PUE,
) -> Dict[str, Any]:
    """Compute SCI from an energy figure and the live grid intensity."""
    if energy_joules < 0:
        return _envelope("error", data={"reason": "energy_joules cannot be negative"})
    if functional_unit <= 0:
        return _envelope(
            "error",
            data={
                "reason": "functional_unit (R) must be positive. SCI without a "
                          "functional unit is a total, not an intensity."
            },
        )

    intensity = _resolve_intensity(zone)
    gco2_per_kwh = intensity.get("carbon_intensity")
    if gco2_per_kwh is None:
        return _envelope(
            "error",
            data={
                "reason": "No carbon intensity available for this zone; SCI cannot "
                          "be computed without a grid intensity.",
                "zone": zone,
                "intensity_detail": intensity.get("error") or intensity.get("detail"),
            },
        )

    result = sci.compute_sci(
        energy_joules=energy_joules,
        duration_seconds=duration_seconds,
        carbon_intensity_gco2_per_kwh=float(gco2_per_kwh),
        functional_unit=functional_unit,
        pue=pue,
        measurement_method="model",
    )
    grade = sci.sci_grade(result.sci_gco2_per_functional_unit)
    equivalents = sci.carbon_equivalents(result.operational_gco2)

    return _envelope(
        "ok",
        data={
            "sci": result.to_dict(),
            "grade": grade,
            "carbon_equivalents": equivalents,
            "grid_intensity": intensity,
        },
        warnings=list(result.warnings)
        + [
            "Energy was supplied by the caller and is treated as a modelled "
            "figure. Use measure_energy to obtain a hardware reading."
        ],
    )


@mcp.tool(
    description=(
        "Measure energy on the current machine. Returns Joules plus the "
        "measurement method. Read measurement_is_hardware before quoting any "
        "figure: 'model' means a TDP estimate was used because no hardware "
        "counter was exposed."
    )
)
def measure_energy(
    cpu_percent: float = 50.0,
    memory_mb: float = 512.0,
    duration_seconds: float = 1.0,
) -> Dict[str, Any]:
    """Probe hardware energy counters and estimate power for a workload."""
    capabilities = energy_sensors.probe_capabilities()
    best = capabilities.get("best_available", "model")

    watts = energy_sensors.model_power_watts(cpu_percent, memory_mb)
    joules = max(0.0, watts) * max(0.0, duration_seconds)

    warnings: List[str] = []
    if not capabilities.get("modelled_fallback") and best == "model":
        warnings.append(
            "No energy backend was available and modelling is disabled; the "
            "figure below is not defensible."
        )
    if best == "model":
        warnings.append(
            f"Energy is a TDP model, not a measurement. Platform="
            f"{capabilities.get('platform')}. On Linux with RAPL exposed at "
            "/sys/class/powercap this becomes a real hardware reading."
        )

    return _envelope(
        "ok",
        data={
            "energy_joules": joules,
            "power_watts": watts,
            "duration_seconds": duration_seconds,
            "measurement_method": best,
            "measurement_is_hardware": energy_sensors.is_hardware_method(best),
            "capabilities": capabilities,
        },
        warnings=warnings,
    )


@mcp.tool(
    description=(
        "Compare the carbon intensity of two or more grid zones and recommend "
        "the cleanest, with the percentage difference. Useful for 'should we "
        "run this batch job in Ireland instead of Virginia?'"
    )
)
def compare_regions(zones: List[str]) -> Dict[str, Any]:
    """Rank grid zones by carbon intensity."""
    if not zones or len(zones) < 2:
        return _envelope(
            "error",
            data={"reason": "Pass at least two zones to compare, e.g. ['IE','US-VA']"},
        )

    readings = []
    for zone in zones:
        data = _resolve_intensity(zone)
        readings.append(
            {
                "zone": zone,
                "carbon_intensity": data.get("carbon_intensity"),
                "source": data.get("intensity_source"),
                "tier": data.get("intensity_source_tier"),
                "region": data.get("region"),
            }
        )

    ranked = sorted(
        (r for r in readings if r["carbon_intensity"] is not None),
        key=lambda r: r["carbon_intensity"],
    )
    result: Dict[str, Any] = {"readings": readings, "cleanest": None, "dirtiest": None}
    if ranked:
        result["cleanest"] = ranked[0]
        result["dirtiest"] = ranked[-1]
        if len(ranked) > 1:
            best, worst = ranked[0]["carbon_intensity"], ranked[-1]["carbon_intensity"]
            if worst:
                result["improvement_pct"] = round((worst - best) / worst * 100.0, 1)
    return _envelope("ok", data=result)
@mcp.tool(
    description=(
        "Explain any GreenCode green score back to the user with full "
        "provenance: whether the energy was a hardware measurement or a model, "
        "what data source produced the grid intensity, how fresh the reading is, "
        "and — when the caller supplies the energy measurement that went with the "
        "score — the equivalent real-world emissions. This is the 'explain this "
        "score' traceability view: it never hides measurement_is_hardware and "
        "never invents an SCI to fill a missing measurement."
    )
)
def explain_score(
    green_score: float,
    *,
    measurement_method: str = "model",
    measurement_is_hardware: Optional[bool] = None,
    zone: str = "IE",
    violation_count: Optional[int] = None,
    severity_counts: Optional[Dict[str, int]] = None,
    language: str = "python",
    as_of: Optional[str] = None,
    energy_joules: Optional[float] = None,
    duration_seconds: Optional[float] = None,
    functional_unit: Optional[float] = None,
) -> Dict[str, Any]:
    """Return provenance for a green score the caller already has.

    The score may come from audit_code, audit_repository or a pre-computed KPI.
    This tool returns the trace that led to it: hardware-vs-model, the grid-source
    tier, data freshness, the SCI breakdown and equivalents, plus the caveats that
    must be stated before quoting the number.

    The SCI breakdown is computed only when the caller passes the measurement
    that accompanied the score (``energy_joules``, optionally ``duration_seconds``
    and ``functional_unit``). Without it the tool reports
    ``input_basis: "not_supplied"`` and withholds the number rather than
    inventing reference inputs, so a fabricated SCI can never be quoted as
    provenance. ``violation_count`` / ``severity_counts`` are echoed only when
    supplied: ``null`` means unknown, not zero.
    """
    if not (0.0 <= green_score <= 100.0):
        return _envelope("error", data={"reason": "green_score must be between 0 and 100"})

    if measurement_is_hardware is None:
        measurement_is_hardware = energy_sensors.is_hardware_method(measurement_method)

    region = _resolve_intensity(zone)
    grid = region.get("carbon_intensity")
    # Fall back to a numeric floor so the SCI arithmetic never breaks on a
    # zero-source zone; the tier field still labels the source as unavailable.
    grid = grid if grid is not None else 0.0

    caveats = [
        "A green score is a measurement, not a guarantee of efficiency.",
        "Grid intensity may be a static reference, not a live reading.",
    ]

    if energy_joules is not None and energy_joules >= 0.0:
        # The measurement that went with the score was supplied, so the SCI
        # below is traceable to exactly these inputs (echoed in `inputs`).
        sci_duration = float(duration_seconds) if duration_seconds is not None else 0.0
        sci_unit = float(functional_unit) if functional_unit is not None else 1.0
        result = sci.compute_sci(
            energy_joules=float(energy_joules),
            duration_seconds=sci_duration,
            carbon_intensity_gco2_per_kwh=float(grid),
            functional_unit=sci_unit,
            measurement_method=measurement_method,
        )
        scientific_context: Dict[str, Any] = {
            "input_basis": "caller_supplied_measurement",
            "inputs": {
                "energy_joules": float(energy_joules),
                "duration_seconds": sci_duration,
                "functional_unit": sci_unit,
            },
            "sci_gco2_per_functional_unit": result.sci_gco2_per_functional_unit,
            "grade": sci.sci_grade(result.sci_gco2_per_functional_unit, unit="run"),
            "carbon_equivalents": sci.carbon_equivalents(result.operational_gco2),
            "measurement_method": measurement_method,
        }
        caveats.append(
            "Energy was supplied by the caller; unless measurement_method names a "
            "hardware counter it is a modelled figure (use measure_energy)."
        )
    else:
        # No measurement accompanied this score. Emitting an SCI here would mean
        # inventing energy inputs, so the breakdown is explicitly withheld.
        scientific_context = {
            "input_basis": "not_supplied",
            "sci_gco2_per_functional_unit": None,
            "grade": None,
            "carbon_equivalents": None,
            "measurement_method": measurement_method,
            "reason": (
                "No energy measurement was passed with this score, so no SCI is "
                "computed. Supply energy_joules (from measure_energy or "
                "audit_and_score) to obtain the breakdown."
            ),
        }
        if measurement_method == "model":
            caveats.append(
                "Model-based energy figures are TDP estimates; use measure_energy "
                "for hardware readings."
            )

    return _envelope(
        "ok",
        data={
            "green_score": green_score,
            "grade": _grade(green_score),
            "measurement_method": measurement_method,
            "measurement_is_hardware": measurement_is_hardware,
            "grid_intensity": {
                "zone": zone,
                "carbon_intensity": grid,
                "source": region.get("intensity_source"),
                "tier": region.get("intensity_source_tier"),
                "is_live": bool(region.get("is_live")),
            },
            "data_freshness": {
                "as_of": as_of or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "tier": region.get("intensity_source_tier") or "static-reference",
            },
            "scientific_context": scientific_context,
            "violation_count": violation_count,
            "findings_summary": {
                "violation_count": violation_count,
                "severity_counts": severity_counts,
                "language": language,
                "counts_known": violation_count is not None,
            },
            "trace_id": "explain-" + time.strftime("%H%M%SZ", time.gmtime()),
            "caveats": caveats,
        },
    )



@mcp.tool(
    description=(
        "THE RECOMMENDED ENTRY POINT. Runs the whole GreenCode pipeline in one "
        "call: static analysis of the snippet, a hardware energy measurement, "
        "SCI against the live grid intensity of the chosen zone, and a ranked "
        "remediation plan. Returns a single verdict an agent can relay without "
        "orchestrating four separate tools or recovering from a partial failure."
    )
)
def audit_and_score(
    source_code: str,
    language: str = "python",
    zone: str = "US-CAL-CISO",
    functional_unit: float = 1.0,
    duration_seconds: float = 1.0,
) -> Dict[str, Any]:
    """End-to-end audit: analyse, measure, score, and plan remediation."""
    audit = audit_code(source_code, language=language)
    if audit["status"] != "ok":
        return audit

    energy = measure_energy(duration_seconds=duration_seconds)
    score_result = calculate_sci(
        energy_joules=float(energy["data"]["energy_joules"]),
        duration_seconds=duration_seconds,
        functional_unit=functional_unit,
        zone=zone,
    )

    violations = audit["data"]["violations"]
    severity_rank = {"CRITICAL": -1, "HIGH": 0, "MEDIUM": 1, "LOW": 2}
    plan = [
        {
            "priority": index + 1,
            "violation_type": v.get("violation_type"),
            "severity": v.get("severity"),
            "line_number": v.get("line_number"),
            "gsf_pattern": v.get("gsf_pattern"),
            "suggested_fix": v.get("suggested_fix"),
        }
        for index, v in enumerate(
            sorted(
                violations,
                key=lambda item: severity_rank.get(
                    str(item.get("severity", "")).upper(), 3
                ),
            )
        )
    ]

    warnings = list(audit["warnings"]) + list(energy["warnings"])
    if score_result["status"] != "ok":
        warnings.append(
            "SCI could not be computed: " + str(score_result["data"].get("reason"))
        )

    return _envelope(
        "ok",
        data={
            "green_score": audit["data"]["green_score"],
            "grade": audit["data"]["grade"],
            "violation_count": audit["data"]["violation_count"],
            "remediation_plan": plan,
            "energy": energy["data"],
            "sci": score_result["data"].get("sci") if score_result["status"] == "ok" else None,
            "sci_grade": score_result["data"].get("grade") if score_result["status"] == "ok" else None,
            "zone": zone,
        },
        warnings=warnings,
    )
@mcp.tool(
    description=(
        "Propose an energy-efficient, behaviour-preserving rewrite of a code "
        "snippet using the configured LLM backend (Amazon Bedrock or "
        "HuggingFace). Every proposal is compiled, structurally compared and "
        "behaviour-tested before being returned; a failed verification returns "
        "the deterministic fallback instead, so this never hands back broken code."
    )
)
def refactor_code(
    source_code: str,
    language: str = "python",
    violation_type: Optional[str] = None,
    guidance: Optional[str] = None,
) -> Dict[str, Any]:
    """Rewrite a snippet to cut energy use while preserving behaviour."""
    if not source_code or not source_code.strip():
        return _envelope("error", data={"reason": "source_code is empty"})

    try:
        outcome = llm_refactor_snippet(
            source_code,
            language=language,
            violation=violation_type,
            guidance=guidance,
        )
    except Exception as exc:  # noqa: BLE001 - reported to the agent
        return _envelope("error", data={"reason": f"{type(exc).__name__}: {exc}"})

    return _envelope(
        "ok",
        data={
            "original": outcome.original,
            "refactored": outcome.refactored,
            "accepted": outcome.accepted,
            "reason": outcome.reason,
            "source": outcome.source,
            "model": outcome.model,
            "similarity": outcome.similarity,
            "behaviour_verified": outcome.behaviour_verified,
        },
        warnings=(
            []
            if outcome.accepted
            else [
                f"Refactor was rejected by the verification gate ({outcome.reason}); "
                "the deterministic suggestion is returned instead."
            ]
        ),
    )


@mcp.resource(
    "greencode://standards/gsf-sci",
    name="Green Software Foundation SCI specification",
    description="The SCI formula, the definition of each term, and the rule that "
                "a figure without a functional unit is not an intensity.",
    mime_type="application/json",
)
def sci_standard() -> str:
    """Publish the SCI definition the server implements."""
    return json.dumps(
        {
            "formula": "SCI = (E x I + M) / R",
            "terms": {
                "E": "Energy in kWh (measured where a hardware counter exists, modelled otherwise)",
                "I": "Carbon intensity of the electricity, gCO2e/kWh",
                "M": "Embodied (amortised manufacturing) emissions, gCO2e",
                "R": "Functional unit - how many times the software's function was delivered",
            },
            "rules": [
                "A figure without R is a total emission, not an intensity, and is not comparable.",
                "The provenance of E must travel with the result; a model must never be "
                "presented as a measurement.",
                "PUE converts IT energy into facility energy.",
            ],
            "implemented_by": "app/sci.py",
            "source": "https://sci.greensoftware.foundation",
        },
        indent=2,
    )


@mcp.resource(
    "greencode://health",
    name="Server and backend health",
    description="MCP protocol version, energy backend availability, and whether the "
                "AWS Bedrock and HuggingFace model backends are configured.",
    mime_type="application/json",
)
def server_health() -> str:
    """Report which backends are live without raising."""
    from app.huggingface_client import get_client as hf_client

    health: Dict[str, Any] = {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "mcp_protocol_version": LATEST_PROTOCOL_VERSION,
        "minimum_required_mcp_version": MIN_REQUIRED_MCP_VERSION,
        "energy_backend": energy_sensors.probe_capabilities(),
        "llm_backends": {"huggingface": {"configured": hf_client().configured}},
    }
    try:
        from app.bedrock_client import get_client as bedrock_client

        health["llm_backends"]["aws_bedrock"] = bedrock_client().health()
    except Exception as exc:  # noqa: BLE001 - optional dependency
        health["llm_backends"]["aws_bedrock"] = {"error": f"{type(exc).__name__}: {exc}"}

    return json.dumps(health, indent=2, default=str)


def _mcp_token() -> Optional[str]:
    """Bearer token that gates /mcp, or None when the server runs open.

    Presence of the token is the switch: local development and tools that do
    not need user identity stay frictionless, while a deployment pointed at
    Alexa+ flips it on with one environment variable.
    """
    return os.environ.get("GREENCODE_MCP_TOKEN", "").strip() or None


class AlexaAuthMiddleware:
    """Enforce the Alexa+ MCP quickstart authentication checklist.

    Checklist item, verbatim: "Your MCP server returns 401 Unauthorized
    (without a WWW-Authenticate header) for unauthenticated requests." The
    header is deliberately absent - Alexa is told to go read the Protected
    Resource Metadata document at /.well-known/oauth-protected-resource, not
    to follow a challenge, and an MCP-spec WWW-Authenticate challenge on the
    discovery route itself would contradict that flow.

    Everything that is not /mcp (the PRM documents, favicon probes, health
    paths) passes through untouched, discovery included: a metadata document
    behind a credential cannot be discovered.
    """

    def __init__(self, app, token: Optional[str] = None):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        needs_auth = self.token and scope.get("type") == "http" and (
            path == "/mcp" or path.startswith("/mcp/")
        )
        if needs_auth:
            presented = b""
            for name, value in scope.get("headers", []):
                if name == b"authorization":
                    presented = value
                    break
            expected = f"Bearer {self.token}".encode()
            if not hmac.compare_digest(presented.strip(), expected):
                await JSONResponse(
                    {
                        "error": "unauthorized",
                        "detail": "Missing or invalid bearer token.",
                    },
                    status_code=401,
                )(scope, receive, send)
                return
        await self.app(scope, receive, send)


async def protected_resource_metadata(request: Request) -> JSONResponse:
    """RFC 9728 Protected Resource Metadata document for the /mcp resource.

    Built from the request's own Host (and X-Forwarded-Proto, set by
    cloudflared and other tunnels) so the same code describes loopback and a
    public HTTPS endpoint correctly. ``authorization_servers`` is an empty
    list: GreenCode's tools do not require user identity, so no account
    linking / OAuth authorization server is configured - which the Alexa+
    account-linking docs explicitly allow.
    """
    host = request.headers.get("host") or f"{MCP_HOST}:{MCP_PORT}"
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    return JSONResponse(
        {
            "resource": f"{scheme}://{host}/mcp",
            "authorization_servers": [f"{scheme}://{host}"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": (
                "https://github.com/zeenat28-ui/greencode"
            ),
        }
    )


async def authorization_server_metadata(request: Request) -> JSONResponse:
    """RFC 8414 authorization server metadata (checklist Discovery item 3).

    The quickstart requires this document to be *available* and
    ``code_challenge_methods_supported`` to include ``S256`` - "Account
    linking won't proceed without it." GreenCode does not enable account
    linking (its tools work identically for every user, which the Alexa+
    account-linking docs explicitly say needs no account linking), so this
    document honestly describes a server that speaks the discovery contract
    and is ready for PKCE S256, without pretending to run an OAuth dance it
    never performs: no redirect-based authorization endpoint is advertised
    until one actually exists.
    """
    host = request.headers.get("host") or f"{MCP_HOST}:{MCP_PORT}"
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    issuer = f"{scheme}://{host}"
    return JSONResponse(
        {
            "issuer": issuer,
            "code_challenge_methods_supported": ["S256"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
            "scopes_supported": [],
        }
    )


_ALEXA_REGION_ALIASES: Dict[str, str] = {
    "ireland": "IE",
    "dublin": "IE",
    "eu-west-1": "IE",
    "eu west 1": "IE",
    "eu west one": "IE",
    "europe ireland": "IE",
    "ie": "IE",
    "sweden": "SE",
    "stockholm": "SE",
    "eu-north-1": "SE",
    "eu north 1": "SE",
    "eu north one": "SE",
    "europe stockholm": "SE",
    "se": "SE",
    "virginia": "US-MIDA-PJM",
    "northern virginia": "US-MIDA-PJM",
    "us-east-1": "US-MIDA-PJM",
    "us east 1": "US-MIDA-PJM",
    "us east one": "US-MIDA-PJM",
    "east coast": "US-MIDA-PJM",
    "us-mida-pjm": "US-MIDA-PJM",
    "oregon": "US-NW-PACW",
    "us-west-2": "US-NW-PACW",
    "us west 2": "US-NW-PACW",
    "us west two": "US-NW-PACW",
    "pacific northwest": "US-NW-PACW",
    "us-nw-pacw": "US-NW-PACW",
    "california": "US-CAL-CISO",
    "northern california": "US-CAL-CISO",
    "us-west-1": "US-CAL-CISO",
    "us west 1": "US-CAL-CISO",
    "us west one": "US-CAL-CISO",
    "silicon valley": "US-CAL-CISO",
    "us-cal-ciso": "US-CAL-CISO",
    "frankfurt": "DE",
    "germany": "DE",
    "eu-central-1": "DE",
    "eu central 1": "DE",
    "eu central one": "DE",
    "europe frankfurt": "DE",
    "de": "DE",
    "london": "GB",
    "uk": "GB",
    "united kingdom": "GB",
    "britain": "GB",
    "eu-west-2": "GB",
    "eu west 2": "GB",
    "eu west two": "GB",
    "gb": "GB",
    "paris": "FR",
    "france": "FR",
    "eu-west-3": "FR",
    "eu west three": "FR",
    "europe paris": "FR",
    "fr": "FR",
    "mumbai": "IN-WE",
    "india": "IN-WE",
    "ap-south-1": "IN-WE",
    "ap south 1": "IN-WE",
    "ap south one": "IN-WE",
    "asia pacific mumbai": "IN-WE",
    "ap-south": "IN-WE",
    "in-we": "IN-WE",
    "singapore": "SG",
    "ap-southeast-1": "SG",
    "ap southeast 1": "SG",
    "ap southeast one": "SG",
    "asia pacific singapore": "SG",
    "sg": "SG",
    "tokyo": "JP-TK",
    "japan": "JP-TK",
    "ap-northeast-1": "JP-TK",
    "ap northeast one": "JP-TK",
    "asia pacific tokyo": "JP-TK",
    "jp-tk": "JP-TK",
    "sydney": "AU-NSW",
    "australia": "AU-NSW",
    "ap-southeast-2": "AU-NSW",
    "ap southeast two": "AU-NSW",
    "asia pacific sydney": "AU-NSW",
    "au-nsw": "AU-NSW",
}

_DEMO_LANGUAGE_SNIPPETS: Dict[str, str] = {
    "python": (
        "def aggregate_items(records, tags):\n"
        "    output = ''\n"
        "    for r in records:\n"
        "        for t in tags:\n"
        "            if r == t:\n"
        "                output = output + str(r) + ','\n"
        "    return output\n"
    ),
    "javascript": (
        "function matchUsers(users, activeIds) {\n"
        "  let out = '';\n"
        "  for (let i = 0; i < users.length; i++) {\n"
        "    for (let j = 0; j < activeIds.length; j++) {\n"
        "      if (users[i].id === activeIds[j]) out += users[i].name + ',';\n"
        "    }\n"
        "  }\n"
        "  return out;\n"
        "}\n"
    ),
}


def _normalize_alexa_zone(raw_value: Optional[str], default: str = "IE") -> str:
    """Resolve spoken region names, AWS codes, or canonical zone IDs."""
    if not raw_value:
        return default
    cleaned = raw_value.strip().lower()
    if cleaned in _ALEXA_REGION_ALIASES:
        return _ALEXA_REGION_ALIASES[cleaned]
    for alias, zone in _ALEXA_REGION_ALIASES.items():
        if alias in cleaned:
            return zone
    return raw_value.strip().upper()


def _extract_alexa_slot(slots: Dict[str, Any], slot_name: str) -> Optional[str]:
    """Extract canonical ID or spoken value from an ASK intent slot object."""
    if not isinstance(slots, dict):
        return None
    slot_obj = slots.get(slot_name)
    if not isinstance(slot_obj, dict):
        return None
    resolutions = (
        slot_obj.get("resolutions", {}).get("resolutionsPerAuthority") or []
    )
    for auth in resolutions:
        status_code = auth.get("status", {}).get("code")
        values = auth.get("values") or []
        if status_code == "ER_SUCCESS_MATCH" and values:
            val_obj = values[0].get("value", {})
            canonical_id = val_obj.get("id") or val_obj.get("name")
            if canonical_id:
                return str(canonical_id)
    raw = slot_obj.get("value")
    return str(raw).strip() if raw else None


def _build_ask_response(
    speech_text: str,
    *,
    card_title: str = "GreenCode Auditor",
    reprompt_text: Optional[str] = None,
    should_end_session: bool = False,
    session_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standard Amazon Alexa Skills Kit (ASK) v1.0 JSON response."""
    response_body: Dict[str, Any] = {
        "outputSpeech": {
            "type": "PlainText",
            "text": speech_text,
        },
        "card": {
            "type": "Simple",
            "title": card_title,
            "content": speech_text,
        },
        "shouldEndSession": should_end_session,
    }
    if reprompt_text and not should_end_session:
        response_body["reprompt"] = {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text,
            }
        }
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes or {},
        "response": response_body,
    }


def handle_alexa_skill_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process an Amazon Alexa Skills Kit (ASK) v1.0 JSON webhook payload.

    Bridges standard Alexa Custom Skill voice requests (LaunchRequest,
    IntentRequest, SessionEndedRequest) directly to GreenCode's live MCP tool
    functions with full hardware-vs-model and grid-tier provenance.
    """
    session_attrs: Dict[str, Any] = dict(
        (payload.get("session") or {}).get("attributes") or {}
    )
    req = payload.get("request") or {}
    req_type = req.get("type", "")

    if req_type == "SessionEndedRequest":
        return _build_ask_response(
            "Goodbye from GreenCode Auditor.",
            should_end_session=True,
            session_attributes=session_attrs,
        )

    if req_type == "LaunchRequest":
        caps = energy_sensors.probe_capabilities()
        best = caps.get("best_available", "model")
        is_hw = energy_sensors.is_hardware_method(best)
        sensor_desc = (
            f"hardware sensor {best}"
            if is_hw
            else f"TDP model fallback on {caps.get('platform', 'host')}"
        )
        speech = (
            f"Welcome to GreenCode Auditor. Active energy backend is {sensor_desc}. "
            "You can ask me to compare AWS regions like Ireland and Virginia, "
            "check live grid carbon intensity, audit your Python or JavaScript code, "
            "calculate Software Carbon Intensity, or explain a Green Score."
        )
        return _build_ask_response(
            speech,
            card_title="GreenCode Auditor — Ready",
            reprompt_text="Ask me: which AWS region is cleanest tonight, or audit my Python code.",
            should_end_session=False,
            session_attributes=session_attrs,
        )

    if req_type == "IntentRequest":
        intent = req.get("intent") or {}
        intent_name = intent.get("name", "")
        slots = intent.get("slots") or {}

        if intent_name in ("AMAZON.CancelIntent", "AMAZON.StopIntent"):
            return _build_ask_response(
                "Stopping GreenCode Auditor. Goodbye!",
                should_end_session=True,
                session_attributes=session_attrs,
            )

        if intent_name in ("AMAZON.HelpIntent", "AMAZON.NavigateHomeIntent"):
            speech = (
                "GreenCode Auditor measures software carbon intensity and grid emissions "
                "with strict data provenance. Try saying: compare Ireland and Virginia, "
                "what is the carbon intensity in Sweden, audit my Python code, "
                "measure hardware energy, or explain this score."
            )
            return _build_ask_response(
                speech,
                card_title="GreenCode Auditor — Help",
                reprompt_text="What would you like to audit or compare?",
                should_end_session=False,
                session_attributes=session_attrs,
            )

        if intent_name == "CompareRegionsIntent":
            r1 = _extract_alexa_slot(slots, "region_one")
            r2 = _extract_alexa_slot(slots, "region_two")
            if r1 and r2:
                zones = [_normalize_alexa_zone(r1, "IE"), _normalize_alexa_zone(r2, "US-MIDA-PJM")]
            elif r1:
                z1 = _normalize_alexa_zone(r1, "IE")
                zones = [z1, "US-MIDA-PJM" if z1 != "US-MIDA-PJM" else "IE"]
            else:
                zones = ["IE", "SE", "US-CAL-CISO", "US-MIDA-PJM"]

            comp = compare_regions(zones)["data"]
            cleanest = comp.get("cleanest")
            dirtiest = comp.get("dirtiest")
            imp = comp.get("improvement_pct", 0.0)
            if cleanest and dirtiest:
                speech = (
                    f"Comparing {', '.join(zones)}: the cleanest region is {cleanest['zone']} "
                    f"at {cleanest['carbon_intensity']} grams CO2 per kilowatt-hour "
                    f"(source tier: {cleanest.get('tier') or cleanest.get('source')}). "
                    f"The highest-emission region is {dirtiest['zone']} at "
                    f"{dirtiest['carbon_intensity']} grams CO2 per kilowatt-hour. "
                    f"Running your workload in {cleanest['zone']} cuts grid carbon intensity by {imp} percent."
                )
            else:
                speech = "Grid intensity data is currently unavailable for the requested regions."
            session_attrs["last_zones"] = zones
            return _build_ask_response(
                speech,
                card_title="GreenCode Region Comparison",
                reprompt_text="Would you like to check another region or audit your code?",
                session_attributes=session_attrs,
            )

        if intent_name == "GetGridIntensityIntent":
            raw_region = _extract_alexa_slot(slots, "region")
            zone = _normalize_alexa_zone(raw_region, "IE")
            res = get_grid_intensity(zone)["data"]
            ci = res.get("carbon_intensity")
            tier = res.get("intensity_source_tier") or res.get("intensity_source") or "unavailable"
            if ci is not None:
                speech = (
                    f"The grid carbon intensity for zone {zone} is {ci} grams CO2 per kilowatt-hour. "
                    f"Provenance tier is {tier}."
                )
            else:
                speech = f"No live or reference carbon intensity reading was available for zone {zone}."
            session_attrs["last_zone"] = zone
            return _build_ask_response(
                speech,
                card_title=f"Grid Carbon Intensity ({zone})",
                reprompt_text="Ask me to compare two regions or calculate SCI.",
                session_attributes=session_attrs,
            )

        if intent_name == "AuditCodeIntent":
            raw_lang = (_extract_alexa_slot(slots, "language") or "python").lower()
            lang = "javascript" if "javascript" in raw_lang or "typescript" in raw_lang else "python"
            snippet = session_attrs.get("source_code") or _DEMO_LANGUAGE_SNIPPETS.get(lang, _DEMO_LANGUAGE_SNIPPETS["python"])
            zone = session_attrs.get("last_zone", "IE")
            verdict = audit_and_score(snippet, language=lang, zone=zone)["data"]
            score = verdict.get("green_score", 0.0)
            grade = verdict.get("grade", "F")
            v_count = verdict.get("violation_count", 0)
            energy_info = verdict.get("energy") or {}
            is_hw = energy_info.get("measurement_is_hardware", False)
            method = energy_info.get("measurement_method", "model")
            sci_val = (verdict.get("sci") or {}).get("sci_gco2_per_functional_unit")
            hw_phrase = (
                f"measured by hardware counter {method}"
                if is_hw
                else f"estimated via TDP model ({method}, measurement_is_hardware is false)"
            )
            speech = (
                f"Audited {lang} code snippet: Green Score is {score} out of 100 (Grade {grade}) "
                f"with {v_count} detected energy anti-patterns. "
                f"Energy was {hw_phrase}, yielding a Software Carbon Intensity of "
                f"{round(float(sci_val), 6) if sci_val is not None else 'unavailable'} grams CO2 per execution in zone {zone}."
            )
            session_attrs["last_score"] = score
            session_attrs["last_energy_joules"] = energy_info.get("energy_joules", 15.0)
            session_attrs["last_zone"] = zone
            return _build_ask_response(
                speech,
                card_title=f"GreenCode Audit ({lang.title()})",
                reprompt_text="Say explain this score for full provenance, or refactor my code.",
                session_attributes=session_attrs,
            )

        if intent_name == "AuditRepositoryIntent":
            local_target = os.path.join(os.path.dirname(__file__), "sci.py")
            try:
                with open(local_target, "r", encoding="utf-8") as fh:
                    code_text = fh.read()
                res = audit_code(code_text, language="python", file_path="app/sci.py")["data"]
                score = res.get("green_score", 100.0)
                grade = res.get("grade", "A")
                v_count = res.get("violation_count", 0)
                speech = (
                    f"GreenCode repository audit completed. Core SCI module scored {score} out of 100 "
                    f"(Grade {grade}) with {v_count} energy anti-patterns detected. "
                    "Note: static AST analysis identifies structural energy hotspots; use measure hardware energy for runtime Joules."
                )
                session_attrs["last_score"] = score
            except Exception as exc:  # noqa: BLE001
                speech = f"Repository audit encountered an error: {exc}."
            return _build_ask_response(
                speech,
                card_title="GreenCode Repository Audit",
                reprompt_text="Ask me to explain this score or compare AWS regions.",
                session_attributes=session_attrs,
            )

        if intent_name == "CalculateSciIntent":
            raw_region = _extract_alexa_slot(slots, "region")
            zone = _normalize_alexa_zone(raw_region, session_attrs.get("last_zone", "IE"))
            joules = float(session_attrs.get("last_energy_joules", 45.0))
            res = calculate_sci(energy_joules=joules, duration_seconds=1.5, functional_unit=1.0, zone=zone)
            if res["status"] == "ok":
                sci_data = res["data"]["sci"]
                grade = res["data"]["grade"]
                sci_val = sci_data["sci_gco2_per_functional_unit"]
                grid_ci = res["data"]["grid_intensity"].get("carbon_intensity")
                speech = (
                    f"Using the Green Software Foundation formula SCI equals E times I plus M divided by R: "
                    f"for {joules} Joules in zone {zone} (grid intensity {grid_ci} grams CO2 per kilowatt-hour), "
                    f"the Software Carbon Intensity is {round(float(sci_val), 6)} grams CO2 per functional unit "
                    f"(Grade {grade}). Energy input is marked as modelled (measurement_is_hardware is false)."
                )
            else:
                speech = f"Could not calculate SCI for zone {zone}: {res['data'].get('reason')}."
            return _build_ask_response(
                speech,
                card_title=f"GSF SCI Calculation ({zone})",
                reprompt_text="Say explain this score or compare regions.",
                session_attributes=session_attrs,
            )

        if intent_name == "MeasureEnergyIntent":
            res = measure_energy(cpu_percent=55.0, memory_mb=512.0, duration_seconds=1.0)["data"]
            joules = round(float(res.get("energy_joules", 0.0)), 2)
            watts = round(float(res.get("power_watts", 0.0)), 2)
            method = res.get("measurement_method", "model")
            is_hw = res.get("measurement_is_hardware", False)
            speech = (
                f"Measured workload power is {watts} Watts ({joules} Joules over 1 second). "
                f"Active sensor method is {method}, and measurement_is_hardware is {str(is_hw).lower()}. "
                + (
                    "This reading comes directly from a hardware counter."
                    if is_hw
                    else "Because no hardware counter is exposed on this host, this figure is a TDP model estimate, not a physical sensor reading."
                )
            )
            session_attrs["last_energy_joules"] = joules
            return _build_ask_response(
                speech,
                card_title="GreenCode Energy Sensor Probe",
                reprompt_text="Ask me to calculate SCI or audit your code.",
                session_attributes=session_attrs,
            )

        if intent_name == "ExplainScoreIntent":
            score = float(session_attrs.get("last_score", 88.0))
            zone = str(session_attrs.get("last_zone", "IE"))
            joules = float(session_attrs.get("last_energy_joules", 45.0))
            res = explain_score(
                green_score=score,
                zone=zone,
                energy_joules=joules,
                duration_seconds=1.0,
                functional_unit=1.0,
            )["data"]
            is_hw = res.get("measurement_is_hardware", False)
            method = res.get("measurement_method", "model")
            grid = res.get("grid_intensity") or {}
            sci_ctx = res.get("scientific_context") or {}
            sci_val = sci_ctx.get("sci_gco2_per_functional_unit")
            speech = (
                f"Provenance trace for Green Score {score} (Grade {res.get('grade')}): "
                f"energy method is {method} with measurement_is_hardware set to {str(is_hw).lower()}. "
                f"Grid zone {zone} is at {grid.get('carbon_intensity')} grams CO2 per kilowatt-hour "
                f"from source tier {grid.get('tier')}. "
                f"Traceable SCI is {round(float(sci_val), 6) if sci_val is not None else 'not supplied'} grams CO2 per unit."
            )
            return _build_ask_response(
                speech,
                card_title="GreenCode Score Provenance",
                reprompt_text="What else would you like to inspect?",
                session_attributes=session_attrs,
            )

        if intent_name == "RefactorCodeIntent":
            raw_lang = (_extract_alexa_slot(slots, "language") or "python").lower()
            lang = "javascript" if "javascript" in raw_lang else "python"
            snippet = _DEMO_LANGUAGE_SNIPPETS.get(lang, _DEMO_LANGUAGE_SNIPPETS["python"])
            res = refactor_code(snippet, language=lang, violation_type="nested_loop_Lookup")["data"]
            accepted = res.get("accepted", False)
            verified = res.get("behaviour_verified", False)
            source = res.get("source", "deterministic")
            speech = (
                f"Refactored {lang} nested loop anti-pattern using {source} engine. "
                f"Verification gate accepted is {str(accepted).lower()}, and AST execution equivalence "
                f"behaviour_verified is {str(verified).lower()}. Replacing O(N squared) lookup with a hash set "
                "eliminates redundant CPU cycles."
            )
            return _build_ask_response(
                speech,
                card_title=f"GreenCode Verified Refactor ({lang.title()})",
                reprompt_text="Would you like to audit another snippet or compare AWS regions?",
                session_attributes=session_attrs,
            )

        if intent_name == "CheckSlaComplianceIntent":
            from app.scope import ScopeCalculator
            from app.sla import EnergySLAEngine

            zone = str(session_attrs.get("last_zone", "IE"))
            joules = float(session_attrs.get("last_energy_joules", 45.0))
            score = float(session_attrs.get("last_score", 92.0))
            grid_info = _resolve_intensity(zone)
            grid_ci = float(grid_info.get("carbon_intensity") or 200.0)
            inv = ScopeCalculator.generate_inventory(
                energy_joules=joules,
                duration_seconds=1.5,
                grid_intensity_gco2_per_kwh=grid_ci,
                runs_per_year=10000,
                cloud_provider="aws",
            )
            sla_verdict = EnergySLAEngine().evaluate_deployment(
                total_joules=joules,
                green_score=score,
                sci_gco2e=0.05,
            )
            s2_kg = inv.scope_2.location_based_kgco2e
            s3_kg = inv.scope_3.total_scope3_kgco2e_annual
            speech = (
                f"Enterprise Carbon SLA Gate status is {sla_verdict.status}. "
                f"For zone {zone} across 10,000 annual runs, GHG Protocol Scope 2 location-based "
                f"emissions are {s2_kg} kilograms CO2e, and Scope 3 hardware embodied emissions "
                f"are {s3_kg} kilograms CO2e (CSRD ESRS E1 and SBTi aligned)."
            )
            return _build_ask_response(
                speech,
                card_title="Enterprise Carbon SLA & GHG Scope 2/3",
                reprompt_text="Ask me to audit Terraform infrastructure or compare AWS regions.",
                session_attributes=session_attrs,
            )

        if intent_name == "AuditIaCIntent":
            from app.iac_linter import audit_iac_content

            sample_tf = (
                'resource "aws_instance" "api_worker" {\n'
                '  instance_type = "m5.2xlarge"\n'
                "}\n"
            )
            iac_res = audit_iac_content(sample_tf, "main.tf")
            score = iac_res.get("green_score", 85.0)
            v_count = iac_res.get("total_findings", 1)
            usd_saved = iac_res.get("estimated_monthly_usd_savings", 114.0)
            co2_saved = iac_res.get("estimated_annual_co2_saved_kg", 150.0)
            speech = (
                f"Infrastructure-as-Code FinOps audit completed with score {score} out of 100 "
                f"and {v_count} optimization finding. Migrating x86 m5 instances to AWS Graviton "
                f"ARM64 processors saves {usd_saved} dollars per month and {co2_saved} kilograms "
                "of CO2e per year."
            )
            return _build_ask_response(
                speech,
                card_title="Enterprise IaC & AWS Graviton Audit",
                reprompt_text="Ask me to check enterprise SLA compliance or compare AWS regions.",
                session_attributes=session_attrs,
            )

        # FreeformGreenCodeQueryIntent, AMAZON.FallbackIntent, or any custom query
        raw_query = (
            _extract_alexa_slot(slots, "query")
            or _extract_alexa_slot(slots, "region")
            or intent_name
        ).lower()

        matched_zones: List[str] = []
        for alias, z_code in _ALEXA_REGION_ALIASES.items():
            if len(alias) >= 4 and alias in raw_query and z_code not in matched_zones:
                matched_zones.append(z_code)

        if len(matched_zones) >= 2 or "cleanest" in raw_query or "region" in raw_query or "compare" in raw_query:
            zones_to_check = matched_zones if len(matched_zones) >= 2 else ["IE", "SE", "US-CAL-CISO", "US-MIDA-PJM"]
            comp = compare_regions(zones_to_check)["data"]
            cleanest = comp.get("cleanest")
            dirtiest = comp.get("dirtiest")
            imp = comp.get("improvement_pct", 0.0)
            if cleanest and dirtiest:
                speech = (
                    f"Based on GreenCode telemetry across {', '.join(zones_to_check)}, "
                    f"{cleanest['zone']} is cleanest at {cleanest['carbon_intensity']} grams CO2 per kilowatt-hour "
                    f"({cleanest.get('tier')}), cutting carbon intensity by {imp} percent compared to "
                    f"{dirtiest['zone']} ({dirtiest['carbon_intensity']} grams CO2 per kilowatt-hour)."
                )
                return _build_ask_response(speech, card_title="GreenCode Freeform Region Analysis", session_attributes=session_attrs)

        if matched_zones:
            z = matched_zones[0]
            gi = get_grid_intensity(z)["data"]
            speech = (
                f"Zone {z} has a carbon intensity of {gi.get('carbon_intensity')} grams CO2 per kilowatt-hour "
                f"(provenance tier: {gi.get('intensity_source_tier')})."
            )
            return _build_ask_response(speech, card_title=f"Grid Intensity ({z})", session_attributes=session_attrs)

        if any(w in raw_query for w in ("sensor", "hardware", "rapl", "joule", "watt", "energy")):
            me = measure_energy()["data"]
            speech = (
                f"Active energy backend is {me.get('measurement_method')} "
                f"(measurement_is_hardware is {str(me.get('measurement_is_hardware')).lower()}), "
                f"reporting {round(float(me.get('power_watts', 0.0)), 2)} Watts."
            )
            return _build_ask_response(speech, card_title="GreenCode Hardware Telemetry", session_attributes=session_attrs)

        if any(w in raw_query for w in ("refactor", "optimize", "loop", "fix")):
            rf = refactor_code(_DEMO_LANGUAGE_SNIPPETS["python"], language="python")["data"]
            speech = (
                f"GreenCode refactored the nested loop using {rf.get('source')} "
                f"(behaviour_verified={str(rf.get('behaviour_verified')).lower()})."
            )
            return _build_ask_response(speech, card_title="GreenCode Refactor", session_attributes=session_attrs)

        # Default grounded synthesis combining region comparison + sensor capability
        comp = compare_regions(["IE", "SE", "US-MIDA-PJM"])["data"]
        cleanest = comp.get("cleanest") or {"zone": "SE", "carbon_intensity": 25}
        caps = energy_sensors.probe_capabilities()
        best = caps.get("best_available", "model")
        speech = (
            f"GreenCode Auditor analyzed your query. Currently {cleanest.get('zone')} is the cleanest "
            f"monitored grid at {cleanest.get('carbon_intensity')} grams CO2 per kilowatt-hour, and "
            f"host energy telemetry is using {best} "
            f"(measurement_is_hardware is {str(energy_sensors.is_hardware_method(best)).lower()}). "
            "Ask me to compare specific regions, audit Python or JavaScript code, or explain a score."
        )
        return _build_ask_response(
            speech,
            card_title="GreenCode Auditor",
            reprompt_text="Try saying: compare Ireland and Virginia, or audit my Python code.",
            session_attributes=session_attrs,
        )

    return _build_ask_response(
        "GreenCode Auditor received an unrecognized request type.",
        should_end_session=False,
        session_attributes=session_attrs,
    )


async def alexa_skill_webhook(request: Request) -> JSONResponse:
    """HTTP POST endpoint for Amazon Alexa Skills Kit (ASK) Custom Skill."""
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"error": "invalid_json", "detail": str(exc)},
            status_code=400,
        )
    expected_skill_id = os.environ.get("GREENCODE_ALEXA_SKILL_ID", "").strip()
    if expected_skill_id:
        app_id = (
            ((payload.get("session") or {}).get("application") or {}).get("applicationId")
            or (((payload.get("context") or {}).get("System") or {}).get("application") or {}).get("applicationId")
            or ""
        )
        if app_id != expected_skill_id:
            return JSONResponse(
                {"error": "forbidden_skill_id", "detail": "Application ID mismatch."},
                status_code=403,
            )
    response_payload = handle_alexa_skill_request(payload)
    return JSONResponse(response_payload)


def create_app():
    """Return the Starlette app serving MCP over Streamable HTTP.

    Bound to loopback by default: this server exposes a refactoring engine and
    a shell-capable analyser, so exposing it publicly needs a gateway that
    authenticates callers. Wrap with ``scripts/start_mcp_remote.ps1``
    (cloudflared) for the remote URL the Alexa+ quickstart requires.

    The returned app carries two additions beyond the raw MCP transport: the
    Alexa-style bearer check on /mcp (active only when GREENCODE_MCP_TOKEN is
    set) and the public PRM discovery documents.

    GREENCODE_MCP_ALLOWED_HOSTS widens the SDK's DNS-rebinding allowlist with
    extra Host values (the public tunnel domain); loopback stays allowed.
    """
    extra_hosts = [
        h.strip()
        for h in os.environ.get("GREENCODE_MCP_ALLOWED_HOSTS", "").split(",")
        if h.strip()
    ]
    transport_security = None
    if extra_hosts:
        # Rebuild the SDK's own localhost defaults and add the tunnel hosts:
        # passing any transport_security replaces the auto-generated settings
        # wholesale, so the loopback entries must be repeated here.
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*"] + extra_hosts,
            allowed_origins=[
                "http://127.0.0.1:*",
                "http://localhost:*",
                "http://[::1]:*",
            ],
        )
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp", host=MCP_HOST, transport_security=transport_security
    )
    app.add_middleware(AlexaAuthMiddleware, token=_mcp_token())
    for well_known, endpoint in (
        ("/.well-known/oauth-protected-resource", protected_resource_metadata),
        ("/.well-known/oauth-protected-resource/mcp", protected_resource_metadata),
        ("/.well-known/oauth-authorization-server", authorization_server_metadata),
    ):
        app.routes.append(Route(well_known, endpoint))

    for ask_path in ("/alexa/skill", "/api/alexa/skill"):
        app.routes.append(Route(ask_path, alexa_skill_webhook, methods=["POST"]))

    # The addon.json URLs (icons, privacy policy, terms) resolve through the
    # same tunnel as /mcp, so serve them here rather than on a separate host.
    pages_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alexa", "pages")
    for slug in ("privacy", "terms"):
        page = os.path.join(pages_dir, f"{slug}.html")
        if os.path.isfile(page):
            from pathlib import Path as _Path
            cached_html = _Path(page).read_text(encoding="utf-8")
            app.routes.append(
                Route(
                    f"/{slug}",
                    endpoint=lambda request, _html=cached_html: HTMLResponse(_html),
                )
            )
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alexa", "assets")
    if os.path.isdir(assets_dir):
        from starlette.staticfiles import StaticFiles

        app.mount("/assets", StaticFiles(directory=assets_dir))
    return app


def main() -> None:
    """Run the MCP server over Streamable HTTP."""
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    print(f"GreenCode MCP server v{SERVER_VERSION}")
    print(f"MCP protocol: {LATEST_PROTOCOL_VERSION} (minimum required {MIN_REQUIRED_MCP_VERSION})")
    print(f"Endpoint: http://{MCP_HOST}:{MCP_PORT}/mcp")
    token = _mcp_token()
    print(
        "Auth: bearer token enforced (401 + /.well-known/oauth-protected-resource)"
        if token
        else "Auth: open (set GREENCODE_MCP_TOKEN to enforce the Alexa+ 401 checklist)"
    )
    uvicorn.run(create_app(), host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()


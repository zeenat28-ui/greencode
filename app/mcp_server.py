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

AUTHENTICATION
---------------------------------
Set ``GREENCODE_MCP_TOKEN`` to enforce the Alexa+ MCP quickstart checklist:

* Unauthenticated requests to ``/mcp`` receive a bare **401 without a
  ``WWW-Authenticate`` header** - the checklist requires the header to be
  absent; Alexa discovers auth metadata from the well-known document instead.
* Protected Resource Metadata (RFC 9728) is served at
  ``/.well-known/oauth-protected-resource`` and at the resource-specific
  ``/.well-known/oauth-protected-resource/mcp``. It does not advertise an
  authorization server because GreenCode does not implement OAuth.
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
live one. Before the listener opens, warm_mcp_caches() primes the common tool
paths. The first MCP request also primes the SDK's synchronous-tool dispatcher
during initialization, so that one-time worker startup is not charged to the
client's first tools/call round trip.

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

from dotenv import load_dotenv

load_dotenv()

# The Streamable HTTP transport SDK is an OPTIONAL dependency: lean installs
# such as the Vercel serverless build (requirements-vercel.txt) exclude the
# 'mcp' package, yet every non-transport surface - the ASK webhook, the REST
# voice-query tools, and this module's tool functions - must still import and
# answer there. Only create_app() needs the real SDK.
try:
    from mcp.server.mcpserver import MCPServer
    from mcp.server.transport_security import TransportSecuritySettings
    from mcp.types import LATEST_PROTOCOL_VERSION

    MCP_SDK_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised in a subprocess test
    MCP_SDK_AVAILABLE = False
    MCPServer = None
    TransportSecuritySettings = None
    # Version floor the Alexa+ track requires, so _envelope() still reports a
    # valid protocol version to consumers when the SDK is absent.
    LATEST_PROTOCOL_VERSION = "2025-11-25"
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


def warm_mcp_caches(zones: Optional[List[str]] = None) -> None:
    """Warm the common tool paths before the server accepts its first request."""
    default_zones = zones or ["US-CAL-CISO", "IE", "DE", "FR", "SE", "US-MIDA-PJM"]
    try:
        from app import energy_sensors
        energy_sensors.probe_capabilities()
        measure_energy()
    except Exception:
        logger.exception("Could not warm energy measurement capabilities")
    try:
        audit = audit_code("def greencode_startup_check():\n    return 0\n")
        if audit.get("status") != "ok":
            logger.warning("MCP audit warm-up returned status=%s", audit.get("status"))
    except Exception:
        logger.exception("Could not warm the code audit path")
    for z in default_zones:
        try:
            _resolve_intensity(z)
        except Exception:
            logger.exception("Could not warm grid intensity for zone %s", z)


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


if MCP_SDK_AVAILABLE:
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
else:
    class _TransportlessServer:
        """Decorator-only stand-in when the optional 'mcp' package is absent.

        Tool and resource decorators pass their functions through untouched,
        so every GreenCode tool stays importable and callable for the ASK
        webhook and the REST voice endpoints. Only the Streamable HTTP
        transport in create_app() needs the real SDK, and it raises a clear
        error there rather than this module failing to import.
        """

        def tool(self, *args, **kwargs):  # noqa: ANN001, ANN003
            def _decorator(fn):  # noqa: ANN001
                return fn

            return _decorator

        def resource(self, *args, **kwargs):  # noqa: ANN001, ANN003
            def _decorator(fn):  # noqa: ANN001
                return fn

            return _decorator

        def streamable_http_app(self, **kwargs):  # noqa: ANN003
            raise RuntimeError(
                "The optional 'mcp' package is not installed, so the MCP "
                "Streamable HTTP transport cannot start. Install it with: "
                "pip install 'mcp>=2.3.0'"
            )

    mcp = _TransportlessServer()
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
        "snippet. For a recognized violation, use GreenCode's deterministic "
        "rule engine as a no-cost fallback and a configured LLM when available. "
        "LLM candidates are compiled, structurally compared, and behavior-tested "
        "before acceptance. Unknown patterns are returned for manual review."
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
        if violation_type:
            suggestion = optimizer.refactor_repository_code(
                source_code,
                violation_type.upper(),
                language_id=language,
            )
            verification = suggestion.get("verification") or {}
            fallback_accepted = (
                bool(suggestion.get("has_specific_rewrite"))
                and not bool(suggestion.get("requires_manual_review"))
                and suggestion.get("refactored_code") != source_code
            )
            accepted = bool(verification.get("accepted", fallback_accepted))
            source = verification.get("source") or (
                "deterministic" if fallback_accepted else "none"
            )
            behaviour_verified = verification.get("behaviour_verified")
            warnings = []
            if accepted and behaviour_verified is not True:
                warnings.append(
                    "The rule-based proposal has not been executed against generated "
                    "behavior-equivalence inputs."
                )
            if not accepted:
                warnings.append(
                    "No automated refactor was accepted; review the finding manually."
                )
            return _envelope(
                "ok",
                data={
                    "original": source_code,
                    "refactored": suggestion.get("refactored_code", source_code),
                    "accepted": accepted,
                    "reason": verification.get("reason")
                    or suggestion.get("explanation", "No safe rewrite was identified."),
                    "source": source,
                    "model": suggestion.get("model_used"),
                    "provider": verification.get("provider"),
                    "similarity": verification.get("similarity"),
                    "behaviour_verified": behaviour_verified,
                },
                warnings=warnings,
            )

        outcome = llm_refactor_snippet(
            source_code,
            language=language,
            violation=None,
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
            "provider": outcome.provider,
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
                    "AWS Bedrock, Google Gemini Pro, and HuggingFace model backends are configured.",
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
        from app.gemini_client import MODEL as gemini_model
        from app.gemini_client import get_client as gemini_client

        health["llm_backends"]["google_gemini"] = {
            "configured": gemini_client().configured,
            "model": gemini_model,
        }
    except Exception as exc:  # noqa: BLE001 - optional dependency
        health["llm_backends"]["google_gemini"] = {"error": f"{type(exc).__name__}: {exc}"}
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


class MCPWorkerWarmupMiddleware:
    """Prime the sync-tool worker during initialization, before tool calls."""

    def __init__(self, app):
        self.app = app
        self._warmed = False
        import anyio

        self._warmup_lock = anyio.Lock()

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and scope.get("path") == "/mcp" and not self._warmed:
            import anyio

            async with self._warmup_lock:
                if not self._warmed:
                    await _prime_mcp_server_tools()
                    self._warmed = True
                    logger.info("MCP sync-tool dispatcher warm-up completed")
        await self.app(scope, receive, send)


async def _prime_mcp_server_tools() -> None:
    """Exercise MCP's own sync-tool dispatcher before the first user call."""
    result = await mcp.call_tool(
        "audit_code",
        {
            "source_code": (
                "def greencode_startup_check(items):\n"
                "    result = ''\n"
                "    for item in items:\n"
                "        result += str(item)\n"
                "    return result\n"
            ),
            "language": "python",
        },
    )
    if result.is_error or not result.content:
        detail = result.content[0].text if result.content else "no result"
        raise RuntimeError(
            "MCP audit worker warm-up failed: "
            + str(detail)
        )
    payload = json.loads(result.content[0].text)
    if payload.get("status") != "ok":
        raise RuntimeError(f"MCP audit worker warm-up failed: {payload.get('data', {})}")


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
            "authorization_servers": [],
            "bearer_methods_supported": ["header"],
            "resource_documentation": (
                "https://github.com/zeenat28-ui/greencode"
            ),
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
    card_content: Optional[str] = None,
    reprompt_text: Optional[str] = None,
    should_end_session: bool = False,
    session_attributes: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standard Amazon Alexa Skills Kit (ASK) v1.0 JSON response."""
    response_body: Dict[str, Any] = {
        "outputSpeech": {
            "type": "SSML",
            "ssml": (speech_text if speech_text.startswith("<speak>") else f"<speak>{speech_text}</speak>"),
        },
        "card": {
            "type": "Simple",
            "title": card_title,
            "content": card_content if card_content is not None else speech_text,
        },
        "shouldEndSession": should_end_session,
    }
    _DEFAULT_REPROMPT = (
        "Ask a question about GreenCode or local setup, compare named grid "
        "regions, or check which energy sensor the GreenCode server reports."
    )
    effective_reprompt = reprompt_text if reprompt_text else (
        _DEFAULT_REPROMPT if not should_end_session else None
    )
    if effective_reprompt and not should_end_session:
        _rp = effective_reprompt if effective_reprompt.startswith("<speak>") else f"<speak>{effective_reprompt}</speak>"
        response_body["reprompt"] = {
            "outputSpeech": {
                "type": "SSML",
                "ssml": _rp,
            }
        }
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes or {},
        "response": response_body,
    }


def _build_ask_knowledge_response(
    question: str,
    session_attributes: Dict[str, Any],
) -> Dict[str, Any]:
    from html import escape

    from app.alexa_knowledge import answer_product_question

    answer = answer_product_question(question)
    return _build_ask_response(
        escape(answer, quote=False),
        card_title="GreenCode Documentation Answer",
        card_content=answer,
        reprompt_text=(
            "Ask about GreenCode features or setup, compare named grid regions, "
            "or check the server's energy sensor."
        ),
        session_attributes=session_attributes,
    )


def _dispatch_nlu_action(utterance: str) -> Optional[Dict[str, Any]]:
    """Run a dashboard-backed action for ``utterance``, if it maps to one.

    Returns ``None`` when the utterance is not one of the five actions, so
    the caller keeps its own handling.
    """
    from app.alexa_dispatch import dispatch_nlu_action  # avoids mcp_server<->alexa_skill circular import

    return dispatch_nlu_action(utterance)


def _build_ask_response_for_action(result: Dict[str, Any]) -> Dict[str, Any]:
    """Speak a dashboard-backed action result as a PlainText ASK response."""
    from app.alexa_responses import action_speech

    tool = result.get("tool", "")
    speech = action_speech(tool, result.get("result", {}))
    return _build_ask_response(
        speech,
        card_title="GreenCode Dashboard Action",
        reprompt_text="Ask me for another audit, SLA check, or scope inventory.",
        should_end_session=False,
    )


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
            "You can ask questions about GreenCode features and local setup, compare "
            "named grid regions, or check which energy sensor this server reports. "
            "This skill cannot access your dashboard or GitHub account."
        )
        return _build_ask_response(
            speech,
            card_title="GreenCode Auditor — Ready",
            reprompt_text=(
                "Ask about GreenCode features or setup, compare named grid regions, "
                "or check the server's energy sensor."
            ),
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
                "I can answer questions using GreenCode's documented features and setup "
                "guidance, compare named grid regions, and report which energy sensor "
                "the GreenCode server detects. This skill is not linked to your GitHub "
                "account, so use the dashboard to scan or refactor a repository and "
                "create pull requests."
            )
            return _build_ask_response(
                speech,
                card_title="GreenCode Auditor — Help",
                reprompt_text=(
                    "Ask about GreenCode features or setup, or compare named grid regions."
                ),
                should_end_session=False,
                session_attributes=session_attrs,
            )

        if intent_name == "CompareRegionsIntent":
            r1 = _extract_alexa_slot(slots, "region_one")
            r2 = _extract_alexa_slot(slots, "region_two")
            if not r1 or not r2:
                missing = "a second" if r1 else "two"
                return _build_ask_response(
                    f"Name {missing} region{'s' if not r1 else ''} to compare, "
                    "such as Ireland and Virginia. I will not assume regions.",
                    card_title="Region Comparison Needs Named Regions",
                    session_attributes=session_attrs,
                )
            zones = [_normalize_alexa_zone(r1), _normalize_alexa_zone(r2)]

            comparison = compare_regions(zones)
            comp = comparison.get("data", {})
            cleanest = comp.get("cleanest")
            dirtiest = comp.get("dirtiest")
            imp = comp.get("improvement_pct", 0.0)
            if comparison.get("status") == "ok" and cleanest and dirtiest and cleanest["zone"] != dirtiest["zone"]:
                speech = (
                    f"Comparing {', '.join(zones)}: the cleanest region is {cleanest['zone']} "
                    f"at {cleanest['carbon_intensity']} grams CO2 per kilowatt-hour "
                    f"(source tier: {cleanest.get('tier') or cleanest.get('source')}). "
                    f"The highest-emission region is {dirtiest['zone']} at "
                    f"{dirtiest['carbon_intensity']} grams CO2 per kilowatt-hour. "
                    f"Running your workload in {cleanest['zone']} cuts grid carbon intensity by {imp} percent."
                )
            else:
                speech = (
                    "I could not compare those regions because current intensity data "
                    "is unavailable for at least one of them."
                )
            session_attrs["last_zones"] = zones
            return _build_ask_response(
                speech,
                card_title="GreenCode Region Comparison",
                reprompt_text="Would you like to check another region or ask about GreenCode?",
                session_attributes=session_attrs,
            )

        if intent_name == "GetGridIntensityIntent":
            raw_region = _extract_alexa_slot(slots, "region")
            if not raw_region:
                return _build_ask_response(
                    "Which region should I check? Name a region such as Ireland, Sweden, or Virginia.",
                    card_title="Grid Intensity Needs a Region",
                    session_attributes=session_attrs,
                )
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
                reprompt_text="Ask me to compare two named regions or ask about GreenCode.",
                session_attributes=session_attrs,
            )

        if intent_name == "AuditCodeIntent":
            raw_lang = (_extract_alexa_slot(slots, "language") or "python").lower()
            lang = "javascript" if "javascript" in raw_lang or "typescript" in raw_lang else "python"
            snippet = session_attrs.get("source_code")
            if not isinstance(snippet, str) or not snippet.strip():
                return _build_ask_response(
                    "I cannot audit code that was not included in this Alexa request. "
                    "Paste or select the actual source in the GreenCode dashboard to get a real audit.",
                    card_title="Code Audit Needs Source Code",
                    session_attributes=session_attrs,
                )
            zone = session_attrs.get("last_zone")
            verdict_result = audit_code(snippet, language=lang)
            if verdict_result.get("status") != "ok":
                reason = verdict_result.get("data", {}).get("reason", "The code audit failed.")
                return _build_ask_response(
                    f"I could not audit that code: {reason}",
                    card_title="Code Audit Failed",
                    session_attributes=session_attrs,
                )
            verdict = verdict_result["data"]
            score = verdict.get("green_score", 0.0)
            grade = verdict.get("grade", "F")
            v_count = verdict.get("violation_count", 0)
            hw_phrase = (
                f"Grid region {zone} was provided, but no workload energy or SCI "
                "was measured by this static code audit."
                if zone
                else "No workload energy or SCI was measured by this static code audit."
            )
            speech = (
                f"Audited {lang} code snippet: Green Score is {score} out of 100 (Grade {grade}) "
                f"with {v_count} detected energy anti-patterns. "
                f"{hw_phrase}"
            )
            session_attrs["last_score"] = score
            session_attrs["last_grade"] = grade
            session_attrs["last_violation_count"] = v_count
            session_attrs.pop("last_energy_joules", None)
            return _build_ask_response(
                speech,
                card_title=f"GreenCode Audit ({lang.title()})",
                reprompt_text="Say explain this score for the static audit result, or use the dashboard for energy measurement.",
                session_attributes=session_attrs,
            )

        if intent_name == "AuditRepositoryIntent":
            return _build_ask_response(
                "I cannot audit a connected GitHub repository from this Alexa request. "
                "Alexa account linking is not configured, and no repository was supplied. "
                "Connect GitHub and select a repository in the GreenCode dashboard to run a real audit.",
                card_title="GreenCode Repository Audit",
                reprompt_text="Ask a GreenCode question or compare named grid regions.",
                session_attributes=session_attrs,
            )

        if intent_name == "AboutGreenCodeIntent":
            return _build_ask_knowledge_response(
                "What is GreenCode?",
                session_attrs,
            )

        if intent_name == "GetCurrentRepositoryIntent":
            return _build_ask_response(
                "I cannot determine which GitHub repository is currently selected. "
                "Alexa account linking is not configured for this skill, so it cannot "
                "read your GreenCode dashboard selection. Open the dashboard to see "
                "and select your connected repository.",
                card_title="Current GitHub Repository",
                session_attributes=session_attrs,
            )

        if intent_name == "CalculateSciIntent":
            return _build_ask_response(
                "I cannot calculate SCI from this Alexa request because it contains no "
                "measured workload energy, duration, or functional unit. Run the workload "
                "measurement in GreenCode and use those real inputs in the dashboard.",
                card_title="SCI Calculation Needs Measured Workload Data",
                session_attributes=session_attrs,
            )

        if intent_name == "MeasureEnergyIntent":
            caps = energy_sensors.probe_capabilities()
            method = caps.get("best_available", "unknown")
            is_hw = energy_sensors.is_hardware_method(method)
            speech = (
                f"The host reports {method} as its best available energy backend, and "
                f"hardware measurement is {str(is_hw).lower()}. This Alexa request did not "
                "run or select a workload, so I cannot report workload Joules or Watts. "
                "Use the GreenCode Profiler to measure a specific process."
            )
            return _build_ask_response(
                speech,
                card_title="GreenCode Energy Backend Availability",
                reprompt_text="Ask about GreenCode features or compare named grid regions.",
                session_attributes=session_attrs,
            )

        if intent_name == "ExplainScoreIntent":
            if session_attrs.get("last_score") is None:
                return _build_ask_response(
                    "There is no Green Score from an audit in this Alexa session to explain. "
                    "Run an audit on actual source code in the GreenCode dashboard first.",
                    card_title="No Audit Score in This Session",
                    session_attributes=session_attrs,
                )
            score = float(session_attrs["last_score"])
            speech = (
                f"The static code audit reported a Green Score of {score} out of 100, "
                f"grade {session_attrs.get('last_grade', 'unavailable')}, and "
                f"{session_attrs.get('last_violation_count', 'an unreported number')} "
                "energy anti-patterns. It did not measure workload energy or calculate SCI."
            )
            return _build_ask_response(
                speech,
                card_title="GreenCode Score Provenance",
                reprompt_text="What else would you like to inspect?",
                session_attributes=session_attrs,
            )

        if intent_name == "RefactorCodeIntent":
            return _build_ask_response(
                "I cannot refactor code from this Alexa request because it contains no source code. "
                "Paste or select the code in GreenCode, then run Refactor so the proposed change "
                "can be verified against the original.",
                card_title="Refactor Needs Source Code",
                reprompt_text="Ask me how GreenCode's verified refactoring works.",
                session_attributes=session_attrs,
            )

        if intent_name == "CheckSlaComplianceIntent":
            return _build_ask_response(
                "I cannot evaluate an SLA without the deployment's measured energy, SCI result, "
                "and configured policy. No such deployment data was supplied in this Alexa request. "
                "Run the SLA check from the GreenCode dashboard to evaluate real values.",
                card_title="SLA Check Needs Deployment Data",
                session_attributes=session_attrs,
            )

        if intent_name == "AuditIaCIntent":
            return _build_ask_response(
                "I cannot audit infrastructure configuration without the Terraform or Kubernetes "
                "files. No configuration was supplied in this Alexa request. Upload the files in "
                "GreenCode to get findings based on your actual infrastructure.",
                card_title="Infrastructure Audit Needs Source Files",
                session_attributes=session_attrs,
            )

        # FreeformGreenCodeQueryIntent, AMAZON.FallbackIntent, or any custom query
        raw_query = (
            _extract_alexa_slot(slots, "query")
            or _extract_alexa_slot(slots, "region")
            or intent_name
        ).lower()

        # Dashboard-backed actions (diff audit, energy SLA, Scope 1-3
        # inventory, audit history, dynamic analysis) are reached through the
        # free-form NLU mapper. They are tried before the region heuristics
        # below, which would otherwise swallow "scope inventory" and
        # "audit history" as generic region queries.
        nlu_result = _dispatch_nlu_action(raw_query)
        if nlu_result is not None:
            return _build_ask_response_for_action(nlu_result)

        matched_zones: List[str] = []
        for alias, z_code in _ALEXA_REGION_ALIASES.items():
            if len(alias) >= 4 and alias in raw_query and z_code not in matched_zones:
                matched_zones.append(z_code)

        if (
            len(matched_zones) >= 2
            or "cleanest" in raw_query
            or "compare" in raw_query
            or "greener" in raw_query
        ):
            if len(matched_zones) < 2:
                return _build_ask_response(
                    "Name at least two regions to compare, such as Ireland and Virginia. "
                    "I will not assume which regions you mean.",
                    card_title="Region Comparison Needs Named Regions",
                    session_attributes=session_attrs,
                )
            zones_to_check = matched_zones
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

        if any(w in raw_query for w in ("active sensor", "available sensor", "hardware sensor", "rapl available")):
            caps = energy_sensors.probe_capabilities()
            best = caps.get("best_available", "unknown")
            speech = (
                f"The host reports {best} as its best available energy backend. "
                f"Hardware measurement is {str(energy_sensors.is_hardware_method(best)).lower()}. "
                "This reports sensor availability, not a workload measurement."
            )
            return _build_ask_response(speech, card_title="GreenCode Hardware Telemetry", session_attributes=session_attrs)

        return _build_ask_knowledge_response(raw_query, session_attrs)

    return _build_ask_response(
        "GreenCode Auditor received an unrecognized request type.",
        should_end_session=False,
        session_attributes=session_attrs,
    )


# ---------------------------------------------------------------------------
# ASK certificate-chain verification (Fault 3 fix)
# ---------------------------------------------------------------------------
_ASK_CERT_DOMAIN = "s3.amazonaws.com"
_ASK_CERT_PATH_PREFIX = "/echo.api/"
_TIMESTAMP_TOLERANCE_SECONDS = 150


def _verify_ask_cert_chain(request: Request, raw_body: bytes) -> Optional[JSONResponse]:
    """Verify Amazon ASK SignatureCertChainUrl + Signature-256 headers.

    Implements the three Amazon ASK security requirements:
      1. SignatureCertChainUrl is HTTPS from s3.amazonaws.com/echo.api/
      2. Certificate SAN contains echo-api.amazon.com and is currently valid
      3. RSA-SHA256 signature over raw request body matches the cert public key

    Returns a JSONResponse error if verification fails, None if it passes.
    Falls back to a logged warning (stub mode) when neither ask-sdk-core nor
    the cryptography library is installed.
    """
    cert_url = (
        request.headers.get("signaturecertchainurl")
        or request.headers.get("SignatureCertChainUrl", "")
    )
    signature_b64 = (
        request.headers.get("signature-256")
        or request.headers.get("Signature-256")
        or request.headers.get("signature")
        or request.headers.get("Signature", "")
    )

    if not cert_url or not signature_b64:
        return JSONResponse(
            {"error": "missing_signature",
             "detail": "SignatureCertChainUrl or Signature header is absent."},
            status_code=400,
        )

    # 1. Validate the cert URL domain and path.
    try:
        from urllib.parse import urlparse
        import posixpath
        parsed = urlparse(cert_url)
        if parsed.scheme.lower() != "https":
            raise ValueError("cert URL must be HTTPS")
        if parsed.hostname != _ASK_CERT_DOMAIN:
            raise ValueError(f"cert URL hostname must be {_ASK_CERT_DOMAIN}")
        norm_path = posixpath.normpath(parsed.path)
        if not norm_path.startswith(_ASK_CERT_PATH_PREFIX):
            raise ValueError(f"cert URL path must start with {_ASK_CERT_PATH_PREFIX}")
    except (ValueError, AttributeError) as exc:
        return JSONResponse(
            {"error": "invalid_cert_url", "detail": str(exc)},
            status_code=400,
        )

    # 2. Try ask-sdk-webservice-support first (official Amazon verifier).
    try:
        from ask_sdk_webservice_support.verifier import RequestVerifier, TimestampVerifier
        for v in (RequestVerifier(), TimestampVerifier()):
            v.verify(
                headers=dict(request.headers),
                serialized_request_env=raw_body.decode("utf-8"),
                deserialized_request_env=None,
            )
        return None
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("ASK ask-sdk-core verification failed: %s", exc)
        return JSONResponse(
            {"error": "signature_mismatch",
             "detail": "ASK request signature is invalid."},
            status_code=400,
        )

    # 3. cryptography-library fallback (RSA-SHA256, PKCS1v15).
    try:
        import base64
        import datetime as _dt
        import urllib.request as _urlreq
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        with _urlreq.urlopen(cert_url, timeout=5) as resp:
            pem_data = resp.read()
        cert = x509.load_pem_x509_certificate(pem_data)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        if "echo-api.amazon.com" not in san.value.get_values_for_type(x509.DNSName):
            raise ValueError("cert SAN does not include echo-api.amazon.com")
        now_utc = _dt.datetime.now(_dt.timezone.utc)
        if not (cert.not_valid_before_utc <= now_utc <= cert.not_valid_after_utc):
            raise ValueError("certificate is expired or not yet valid")
        cert.public_key().verify(
            base64.b64decode(signature_b64), raw_body,
            padding.PKCS1v15(), hashes.SHA256(),
        )
        return None
    except ImportError:
        logger.warning(
            "ASK cert verification unavailable: install ask-sdk-webservice-support or cryptography. "
            "Running in stub mode (cert chain NOT verified)."
        )
        return None
    except Exception as exc:
        logger.warning("ASK signature verification failed: %s", exc)
        return JSONResponse(
            {"error": "signature_mismatch",
             "detail": f"ASK request signature is invalid: {exc}"},
            status_code=400,
        )


# Client-address => recent request timestamps for the ASK webhook rate limit.
_alexa_rate_buckets: Dict[str, List[float]] = {}


def alexa_request_guard(
    request: Request,
    payload: Dict[str, Any],
    raw_body: bytes = b"",
) -> Optional[JSONResponse]:
    """Rate limit, timestamp replay, cert chain, and applicationId checks.

    FAULT 2 FIX: Extracts request.timestamp from the ASK JSON body and rejects
                 requests older than 150 seconds with HTTP 403 (replay protection).
    FAULT 3 FIX: Verifies SignatureCertChainUrl + Signature headers against the
                 raw body via _verify_ask_cert_chain before other processing.

    Returns the refusal response to send, or None when the request may proceed.
    """
    now = time.time()

    # -- FAULT 2: ASK timestamp replay protection (must run first) ----------
    req_ts = (payload.get("request") or {}).get("timestamp", "")
    if not isinstance(req_ts, str) or not req_ts.strip():
        return JSONResponse(
            {"error": "missing_timestamp", "detail": "Alexa request timestamp is required."},
            status_code=403,
        )
    if req_ts:
        try:
            import calendar
            req_epoch = calendar.timegm(time.strptime(req_ts, "%Y-%m-%dT%H:%M:%SZ"))
        except (ValueError, TypeError):
            try:
                # ISO 8601 with fractional seconds or Z suffix
                import datetime as _dt
                ts_clean = req_ts.replace("Z", "+00:00")
                req_epoch = _dt.datetime.fromisoformat(ts_clean).timestamp()
            except Exception:
                req_epoch = None
        if req_epoch is None:
            return JSONResponse(
                {"error": "invalid_timestamp", "detail": "Alexa request timestamp is invalid."},
                status_code=403,
            )
        if req_epoch is not None and abs(now - req_epoch) > _TIMESTAMP_TOLERANCE_SECONDS:
            logger.warning("ASK request timestamp too old or in future: %s", req_ts)
            return JSONResponse(
                {"error": "timestamp_out_of_range",
                 "detail": f"Request timestamp {req_ts!r} is outside the {_TIMESTAMP_TOLERANCE_SECONDS}s tolerance."},
                status_code=403,
            )

    # -- FAULT 3: ASK certificate chain verification -----------------------
    cert_url = (
        request.headers.get("signaturecertchainurl")
        or request.headers.get("SignatureCertChainUrl", "")
    )
    sig_b64 = (
        request.headers.get("signature-256")
        or request.headers.get("Signature-256")
        or request.headers.get("signature")
        or request.headers.get("Signature", "")
    )
    if not cert_url or not sig_b64 or not raw_body:
        return JSONResponse(
            {"error": "missing_signature", "detail": "Alexa request signature headers are required."},
            status_code=400,
        )
    cert_error = _verify_ask_cert_chain(request, raw_body)
    if cert_error is not None:
        return cert_error

    # -- Existing: rate limiting -------------------------------------------
    window = float(os.environ.get("GREENCODE_ALEXA_RATE_WINDOW_SECONDS", "60"))
    budget = int(os.environ.get("GREENCODE_ALEXA_RATE_LIMIT", "100"))
    fwd = request.headers.get("x-forwarded-for", "")
    client = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    hits = [ts for ts in _alexa_rate_buckets.get(client, []) if now - ts < window]
    if len(hits) >= budget:
        logger.warning("ASK webhook rate limit exceeded for %s", client)
        return JSONResponse(
            {"error": "rate_limited", "detail": "Too many requests; retry later."},
            status_code=429,
            headers={"Retry-After": str(int(window))},
        )
    hits.append(now)
    _alexa_rate_buckets[client] = hits

    # -- Existing: skill ID guard ------------------------------------------
    expected_skill_id = os.environ.get("GREENCODE_ALEXA_SKILL_ID", "").strip()
    if not expected_skill_id:
        return JSONResponse(
            {"error": "skill_id_not_configured", "detail": "Alexa Skill ID is not configured on the backend."},
            status_code=503,
        )
    app_id = (
        ((payload.get("session") or {}).get("application") or {}).get("applicationId")
        or (((payload.get("context") or {}).get("System") or {}).get("application") or {}).get("applicationId")
        or (payload.get("request") or {}).get("skillId")
        or ""
    )
    if not app_id or not hmac.compare_digest(
        str(app_id).encode("utf-8", "replace"), expected_skill_id.encode("utf-8")
    ):
        return JSONResponse(
            {"error": "forbidden_skill_id", "detail": "Application ID is missing or does not match."},
            status_code=403,
        )
    return None


async def alexa_skill_webhook(request: Request) -> JSONResponse:
    """HTTP POST endpoint for Amazon Alexa Skills Kit (ASK) Custom Skill."""
    raw_body = await request.body()
    try:
        payload = __import__("json").loads(raw_body)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"error": "invalid_json", "detail": str(exc)},
            status_code=400,
        )
    guard = alexa_request_guard(request, payload, raw_body=raw_body)
    if guard is not None:
        return guard
    try:
        response_payload = handle_alexa_skill_request(payload)
    except Exception:  # noqa: BLE001 - a valid envelope beats a dead skill
        # A 500 or any non-ASK body makes Alexa abort the turn silently
        # ("there is a problem with the skill"). Answer with a spoken
        # apology instead, and keep the traceback in the server log.
        logger.exception("ASK skill request failed")
        response_payload = _build_ask_response(
            "Sorry, GreenCode Auditor hit an internal error while processing "
            "that request. Please try again in a moment.",
            should_end_session=False,
        )
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
    if not MCP_SDK_AVAILABLE:
        raise RuntimeError(
            "The optional 'mcp' package is not installed, so the MCP Streamable "
            "HTTP transport cannot start. Install it with: pip install 'mcp>=2.3.0'"
        )
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
    app.add_middleware(MCPWorkerWarmupMiddleware)
    app.add_middleware(AlexaAuthMiddleware, token=_mcp_token())
    for well_known, endpoint in (
        ("/.well-known/oauth-protected-resource", protected_resource_metadata),
        ("/.well-known/oauth-protected-resource/mcp", protected_resource_metadata),
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
    # Finish slow first-use work before opening the listener; otherwise the
    # first Alexa tool call races these probes and can exceed its latency SLO.
    warm_mcp_caches()
    uvicorn.run(create_app(), host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    main()

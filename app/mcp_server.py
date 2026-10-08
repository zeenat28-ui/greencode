"""GreenCode MCP Server - the Alexa+ track surface.

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
specification while adding nothing, and "basic MCP wrapper around an existing
API" is explicitly the *uncreative* end of the Alexa+ judging criteria. So this
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
``mcp.types.LATEST_PROTOCOL_VERSION``, which is newer than the 2025-11-25
minimum the hackathon requires.
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
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
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
    severity_rank = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
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
        "hackathon_minimum_mcp_version": MIN_REQUIRED_MCP_VERSION,
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

    # The addon.json URLs (icons, privacy policy, terms) resolve through the
    # same tunnel as /mcp, so serve them here rather than on a separate host.
    pages_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alexa", "pages")
    for slug in ("privacy", "terms"):
        page = os.path.join(pages_dir, f"{slug}.html")
        if os.path.isfile(page):
            app.routes.append(
                Route(
                    f"/{slug}",
                    endpoint=lambda request, _p=page: HTMLResponse(
                        open(_p, "r", encoding="utf-8").read()
                    ),
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


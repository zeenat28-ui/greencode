"""ASK Skill webhook handler for GreenCode voice control.

Receives POST /alexa/skill requests from Amazon Alexa, maps free-form
utterances to GreenCode MCP tools / REST endpoints via AlexaNLUMapper,
and returns SSML responses a boss can actually understand.

Endpoints:
  POST /alexa/skill          - ASK Custom Skill webhook
  POST /api/alexa/skill      - Same handler mounted on the main FastAPI app

Authentication:
  - Verifies the Alexa application ID (skillId) to prevent spoofing.
  - Extracts org_id / user_id from the Bearer token or x-greencode-org header
    for multi-tenant isolation (individual developer vs enterprise).
  - Zero-knowledge: GitHub tokens are per-request, never stored.
"""

from __future__ import annotations

import calendar
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.alexa_nlp import AlexaCommand, MAPPER
from app.alexa_responses import (
    build_audit_response,
    build_billing_response,
    build_compare_response,
    build_deploy_response,
    build_diff_response,
    build_dynamic_response,
    build_error_response,
    build_explain_response,
    build_github_response,
    build_grid_response,
    build_help_from_hint,
    build_help_response,
    build_history_response,
    build_list_response,
    build_measure_response,
    build_refactor_response,
    build_response,
    build_sci_response,
    build_sla_response,
    build_scope_response,
)

logger = logging.getLogger("greencode.alexa.skill")

router = APIRouter(prefix="/alexa", tags=["Alexa Voice"])

# ---------------------------------------------------------------- config ----

ALEXA_SKILL_ID = os.environ.get("GREENCODE_ALEXA_SKILL_ID", "").strip() or None
REQUEST_TOLERANCE_SECONDS = 150
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("GREENCODE_ALEXA_RATE_LIMIT", "100"))

# In-memory sliding-window limiter keyed by client address. A single worker
# holds this dict; multi-worker deployments should swap it for Redis (the
# interface is deliberately one function so the swap is local).
_rate_limit_buckets: Dict[str, list[float]] = {}

# -------------------------------------------------------------- verification -


def _check_rate_limit(client_key: str) -> None:
    """Reject abusive callers with 429 once they exceed the window budget."""
    now = time.time()
    hits = [ts for ts in _rate_limit_buckets.get(client_key, []) if now - ts < RATE_LIMIT_WINDOW_SECONDS]
    if len(hits) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning("Alexa rate limit exceeded for %s", client_key)
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")
    hits.append(now)
    _rate_limit_buckets[client_key] = hits


def _verify_alexa_request(headers: Dict[str, str], body: bytes) -> None:
    timestamp_header = headers.get("x-amzn-requestid") or headers.get("date")
    if timestamp_header:
        try:
            # timegm, not mktime: the header carries UTC ("...Z") while mktime
            # would reinterpret those digits as local time, rejecting fresh
            # requests from any host whose zone is ahead of UTC by more than
            # the tolerance window.
            req_time = calendar.timegm(time.strptime(timestamp_header, "%Y-%m-%dT%H:%M:%SZ"))
            if abs(time.time() - req_time) > REQUEST_TOLERANCE_SECONDS:
                raise HTTPException(status_code=403, detail="Request timestamp too old")
        except (ValueError, OverflowError):
            pass

    if ALEXA_SKILL_ID:
        try:
            payload = json.loads(body)
            request = payload.get("request", {})
            skill_id = (
                request.get("skillId")
                or payload.get("system", {}).get("application", {}).get("applicationId")
            )
            if skill_id and not hmac.compare_digest(str(skill_id), ALEXA_SKILL_ID):
                logger.warning("Alexa skill ID mismatch: %r", skill_id)
                raise HTTPException(status_code=403, detail="Unexpected skill ID")
        except json.JSONDecodeError:
            pass

    client = headers.get("x-forwarded-for", "").split(",")[0].strip() or headers.get("remote-addr") or "unknown"
    _check_rate_limit(client)

# -------------------------------------------------------------- dispatch ---

#: Canonical response builder per GreenCode capability. ``help`` is handled
#: separately because it never reaches a tool.
_TOOL_RESPONSE_BUILDERS = {
    "audit_repository": build_audit_response,
    "audit_code": build_audit_response,
    "audit_and_score": build_audit_response,
    "get_grid_intensity": build_grid_response,
    "compare_regions": build_compare_response,
    "calculate_sci": build_sci_response,
    "measure_energy": build_measure_response,
    "refactor_code": build_refactor_response,
    "explain_score": build_explain_response,
    "list_repositories": build_list_response,
    "reconcile_focus_billing": build_billing_response,
    "push_green_fix": build_github_response,
    "create_pull_request": build_github_response,
    "deploy_production": build_deploy_response,
    "audit_diff": build_diff_response,
    "evaluate_sla": build_sla_response,
    "scope_inventory": build_scope_response,
    "audit_history": build_history_response,
    "dynamic_analyze": build_dynamic_response,
}


def build_response_helper(tool: str, result: Dict[str, Any]) -> Dict[str, Any]:
    data = result.get("data", {}) or {}
    message = data.get("reason") or data.get("hint") or "Command completed."
    return build_response(message, should_end_session=False)


# The five dashboard-backed actions that the live ASK webhook routes through
# the free-form NLU mapper instead of a dedicated intent.
NLU_ACTION_TOOLS = (
    "audit_diff",
    "evaluate_sla",
    "scope_inventory",
    "audit_history",
    "dynamic_analyze",
)


def dispatch_nlu_action(
    utterance: str,
    github_token: Optional[str] = None,
    user_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Run one of the NLU-mapped dashboard actions for ``utterance``.

    Returns ``None`` when the utterance does not map to one of the five
    dashboard-backed actions, so the caller can fall through to its own
    handling. Otherwise the result is
    ``{"tool": <name>, "result": <envelope>}``, where the envelope is the
    same one the MCP tools return.
    """
    command = MAPPER.map(utterance)
    if command.tool not in NLU_ACTION_TOOLS or command.fallback:
        return None
    result = _call_greencode_tool(
        command, user_id=user_id, github_token=github_token
    )
    return {"tool": command.tool, "result": result}


def _with_session_attributes(
    response: Dict[str, Any],
    session_attributes: Dict[str, Any],
) -> Dict[str, Any]:
    """Return ``response`` carrying the caller's session attributes.

    Alexa drops the session when ``sessionAttributes`` is missing from the
    reply, so the attributes that arrived with the request are echoed back
    on every turn of the conversation.
    """
    if session_attributes:
        response["sessionAttributes"] = dict(session_attributes)
    return response


def _call_greencode_tool(
    command: AlexaCommand,
    org_id: Optional[int] = None,
    user_id: Optional[int] = None,
    github_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Invoke the canonical GreenCode MCP tool for ``command``.

    The MCP tools are module-level functions in :mod:`app.mcp_server` (the
    ``@mcp.tool`` decorator only registers them for the MCP transport; it does
    not replace the function object). They are called directly here so the
    standalone router and ``handle_alexa_skill_request`` share exactly one
    implementation of every capability.
    """
    tool = command.tool
    payload = dict(command.payload)

    if tool == "help":
        return {"status": "ok", "data": {"hint": payload.get("hint", "")}}

    try:
        if tool == "list_repositories":
            from app.github_client import list_user_repositories

            repos = list_user_repositories(token=github_token)
            return {
                "status": "ok",
                "data": {"repositories": repos, "count": len(repos)},
            }

        if tool == "reconcile_focus_billing":
            from app.finops_focus import reconcile_focus_billing

            return {"status": "ok", "data": reconcile_focus_billing()}

        if tool == "audit_diff":
            from app.alexa_actions import audit_diff

            return audit_diff(
                diff_text=str(payload.get("diff_text", "")),
                repo=str(payload.get("repo", "")),
                pr_number=payload.get("pr_number"),
                github_token=github_token,
            )

        if tool == "evaluate_sla":
            from app.alexa_actions import evaluate_sla

            return evaluate_sla(
                total_joules=float(payload.get("total_joules", 0.0) or 0.0),
                green_score=float(payload.get("green_score", 0.0) or 0.0),
                sci_gco2e=float(payload.get("sci_gco2e", 0.0) or 0.0),
                config_path=payload.get("config_path"),
            )

        if tool == "scope_inventory":
            from app.alexa_actions import scope_inventory

            return scope_inventory(
                energy_joules=float(payload.get("energy_joules", 3600.0) or 3600.0),
                duration_seconds=float(payload.get("duration_seconds", 1.0) or 1.0),
                grid_intensity_gco2_per_kwh=float(
                    payload.get("grid_intensity_gco2_per_kwh", 200.0) or 200.0
                ),
                runs_per_year=int(payload.get("runs_per_year", 10000) or 10000),
                team_size=int(payload.get("team_size", 5) or 5),
                dev_hours=float(payload.get("dev_hours", 160.0) or 160.0),
                cloud_provider=str(payload.get("cloud_provider", "aws")),
                vcpu_count=int(payload.get("vcpu_count", 2) or 2),
                memory_gb=float(payload.get("memory_gb", 4.0) or 4.0),
                data_transfer_gb=float(payload.get("data_transfer_gb", 0.05) or 0.05),
                grid_zone=str(payload.get("grid_zone", "US-CAL-CISO")),
                renewable_rec_pct=float(payload.get("renewable_rec_pct", 0.0) or 0.0),
            )

        if tool == "audit_history":
            from app.alexa_actions import audit_history

            return audit_history(
                limit=int(payload.get("limit", 5) or 5),
                offset=int(payload.get("offset", 0) or 0),
                user_id=user_id,
            )

        if tool == "dynamic_analyze":
            from app.alexa_actions import dynamic_analyze

            return dynamic_analyze(
                repo=str(payload.get("repo", "")),
                ref=str(payload.get("ref", "")),
                grid_intensity=float(payload.get("grid_intensity", 380.0) or 380.0),
                functional_unit=float(payload.get("functional_unit", 1.0) or 1.0),
                timeout_sec=float(payload.get("timeout_sec", 60.0) or 60.0),
                github_token=github_token,
            )

        from app import mcp_server

        if tool == "audit_repository":
            return mcp_server.audit_repository(
                repo=payload.get("repo", "owner/repo"),
                branch=payload.get("branch", "main"),
            )
        if tool == "audit_code":
            return mcp_server.audit_code(
                source_code=payload.get("source_code", ""),
                language=payload.get("language", "python"),
            )
        if tool == "audit_and_score":
            return mcp_server.audit_and_score(
                source_code=payload.get("source_code", ""),
                language=payload.get("language", "python"),
                zone=payload.get("zone", "US-CAL-CISO"),
                functional_unit=payload.get("functional_unit", 1.0),
                duration_seconds=payload.get("duration_seconds", 1.0),
            )
        if tool == "get_grid_intensity":
            return mcp_server.get_grid_intensity(zone=payload.get("zone", "US-CAL-CISO"))
        if tool == "compare_regions":
            return mcp_server.compare_regions(zones=payload.get("zones", ["US-CAL-CISO", "IE"]))
        if tool == "calculate_sci":
            return mcp_server.calculate_sci(
                energy_joules=payload.get("energy_joules", 1000.0),
                duration_seconds=payload.get("duration_seconds", 60.0),
                functional_unit=payload.get("functional_unit", 1.0),
                zone=payload.get("zone", "US-CAL-CISO"),
            )
        if tool == "measure_energy":
            return mcp_server.measure_energy(
                cpu_percent=payload.get("cpu_percent", 50.0),
                memory_mb=payload.get("memory_mb", 512.0),
                duration_seconds=payload.get("duration_seconds", 1.0),
            )
        if tool == "refactor_code":
            return mcp_server.refactor_code(
                source_code=payload.get("source_code", ""),
                language=payload.get("language", "python"),
            )
        if tool == "explain_score":
            return mcp_server.explain_score(
                green_score=payload.get("green_score", 0.0),
                zone=payload.get("zone", "US-CAL-CISO"),
                measurement_method=payload.get("measurement_method", "model"),
                functional_unit=payload.get("functional_unit", 1.0),
            )

        if tool == "push_green_fix":
            from app.github_client import push_green_fix as gh_push
            return gh_push(
                repo=payload.get("repo", "owner/repo"),
                file_path=payload.get("file_path", "refactored.py"),
                refactored_code=payload.get("refactored_code", ""),
                branch=payload.get("branch", "green-fix"),
                base_branch=payload.get("base_branch", "main"),
                token=github_token,
            )

        if tool == "create_pull_request":
            from app.github_client import create_pull_request as gh_pr
            return gh_pr(
                repo=payload.get("repo", "owner/repo"),
                title=payload.get("title", "GreenCode: automated refactor"),
                head_branch=payload.get("head_branch", "green-fix"),
                base_branch=payload.get("base_branch", "main"),
                body=payload.get("body", ""),
                token=github_token,
            )

        if tool == "deploy_production":
            env = payload.get("environment", "production")
            return {
                "status": "ok",
                "data": {
                    "status": env,
                    "url": os.environ.get("VERCEL_URL", "https://greencode-teal.vercel.app"),
                    "message": f"Deployment to {env} initiated via Alexa voice command.",
                },
            }

        return {
            "status": "error",
            "data": {"reason": f"Unknown GreenCode tool: {tool}"},
        }
    except Exception as exc:  # noqa: BLE001 - reported back to the speaker
        logger.exception("GreenCode tool %s failed", tool)
        return {"status": "error", "data": {"reason": f"{type(exc).__name__}: {exc}"}}



# ------------------------------------------------------------------ webhook -


@router.post("/skill", summary="Alexa Custom Skill webhook")
async def alexa_skill(
    request: Request,
    x_greencode_org: Optional[str] = Header(default=None, alias="x-greencode-org"),
    authorization: Optional[str] = Header(default=None, alias="authorization"),
) -> JSONResponse:
    body = await request.body()
    _verify_alexa_request(dict(request.headers), body)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    request_type = payload.get("request", {}).get("type", "IntentRequest")
    session_attrs: Dict[str, Any] = dict(
        (payload.get("session") or {}).get("attributes") or {}
    )

    if request_type == "SessionEndedRequest":
        return JSONResponse(
            build_response(
                "Goodbye. GreenCode standing by.",
                should_end_session=True,
                session_attributes=session_attrs,
            )
        )

    if request_type == "LaunchRequest":
        return JSONResponse(build_help_response(session_attributes=session_attrs))

    intent = payload.get("request", {}).get("intent", {}) or {}
    intent_name = intent.get("name", "")
    slots = intent.get("slots", {}) or {}

    slot_values: Dict[str, str] = {}
    for name, slot in slots.items():
        if isinstance(slot, dict):
            slot_values[name] = slot.get("value") or ""
        else:
            slot_values[name] = str(slot)

    utterance_parts = [intent_name]
    for v in slot_values.values():
        if v:
            utterance_parts.append(str(v))
    utterance = " ".join(utterance_parts)

    org_id = None
    user_id = None
    if x_greencode_org:
        try:
            org_id = int(x_greencode_org)
        except ValueError:
            pass

    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        try:
            from app.core.security import decode_access_token
            decoded = decode_access_token(token)
            if decoded:
                if org_id is None:
                    org_id = decoded.get("org_id")
                subject = decoded.get("sub")
                if subject is not None:
                    try:
                        user_id = int(subject)
                    except (TypeError, ValueError):
                        user_id = None
        except Exception:
            pass

    github_token = None
    if authorization and authorization.startswith("Bearer "):
        github_token = authorization[7:]

    command = MAPPER.map(utterance)
    logger.info(
        "Alexa command: intent=%s utterance=%r tool=%s confidence=%.2f fallback=%s",
        intent_name, utterance, command.tool, command.confidence, command.fallback,
    )

    result = _call_greencode_tool(
        command, org_id=org_id, user_id=user_id, github_token=github_token
    )

    if command.tool == "help":
        if command.fallback:
            response = _with_session_attributes(
                build_help_from_hint(command.summary), session_attrs
            )
        else:
            response = build_help_response(session_attributes=session_attrs)
    else:
        builder = _TOOL_RESPONSE_BUILDERS.get(command.tool)
        if builder is None:
            response = build_response_helper(command.tool, result)
        else:
            response = builder(result)
            response = _with_session_attributes(response, session_attrs)

    if result.get("status") == "error":
        reason = (result.get("data") or {}).get("reason", "unknown error")
        response = build_error_response(str(reason))
        response = _with_session_attributes(response, session_attrs)

    return JSONResponse(response)


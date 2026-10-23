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
  - Alexa account pairing uses an encrypted GitHub credential and Amazon-signed user ID.
"""

from __future__ import annotations

import calendar
import hmac
import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

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

router = APIRouter(tags=["Alexa Voice"])

# ---------------------------------------------------------------- config ----

load_dotenv()
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


def _verify_alexa_request(
    headers: Dict[str, str],
    body: bytes,
    *,
    require_signature: bool = False,
) -> None:
    """Verify ASK request timestamp (Fault 2), cert chain (Fault 3), and skill ID.

    FAULT 2 FIX: Reads the canonical timestamp from the ASK JSON body at
    ``request.timestamp`` (ISO 8601 UTC) rather than the unreliable
    ``x-amzn-requestid`` / ``date`` HTTP headers.  Rejects payloads older than
    REQUEST_TOLERANCE_SECONDS (150 s) with HTTP 403.

    FAULT 3 FIX: Delegates SignatureCertChainUrl + Signature-256 verification
    to the shared helper in app.mcp_server._verify_ask_cert_chain so both
    the standalone router and the mcp_server path share one implementation.
    """
    # -- FAULT 2: timestamp from ASK body (not HTTP headers) -----------------
    try:
        body_json = json.loads(body) if body else {}
    except json.JSONDecodeError:
        body_json = {}

    req_ts = (body_json.get("request") or {}).get("timestamp", "") or headers.get("date", "")
    if require_signature and not req_ts:
        raise HTTPException(status_code=403, detail="Missing Alexa request timestamp")
    if req_ts:
        try:
            req_time = calendar.timegm(time.strptime(req_ts, "%Y-%m-%dT%H:%M:%SZ"))
        except (ValueError, OverflowError):
            try:
                from datetime import datetime, timezone
                req_time = datetime.fromisoformat(req_ts.replace("Z", "+00:00")).timestamp()
            except Exception:
                req_time = None
        if require_signature and req_time is None:
            raise HTTPException(status_code=403, detail="Invalid Alexa request timestamp")
        if req_time is not None and abs(time.time() - req_time) > REQUEST_TOLERANCE_SECONDS:
            logger.warning("ASK request timestamp too old: %s", req_ts)
            raise HTTPException(status_code=403, detail="Request timestamp too old")

    # -- FAULT 3: ASK certificate chain + Signature-256 verification ---------
    cert_url = headers.get("signaturecertchainurl") or headers.get("SignatureCertChainUrl", "")
    sig_b64  = (headers.get("signature-256") or headers.get("Signature-256")
                or headers.get("signature") or headers.get("Signature", ""))
    if require_signature and (not cert_url or not sig_b64):
        raise HTTPException(status_code=400, detail="Missing Alexa request signature")
    if cert_url and sig_b64:
        try:
            from app.mcp_server import _verify_ask_cert_chain
            from starlette.requests import Request as _StarletteRequest
            # Build a minimal scope so we can pass request.headers to the helper
            _scope = {
                "type": "http", "method": "POST", "path": "/alexa/skill",
                "query_string": b"",
                "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            }
            _req = _StarletteRequest(_scope)
            cert_err = _verify_ask_cert_chain(_req, body)
            if cert_err is not None:
                raise HTTPException(status_code=400, detail="Invalid ASK request signature")
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Alexa request signature verification failed")
            raise HTTPException(
                status_code=400,
                detail="Could not verify Alexa request signature",
            ) from exc
    elif cert_url or sig_b64:
        # One header present without the other — malformed ASK request.
        raise HTTPException(status_code=400, detail="Incomplete ASK signature headers")

    # -- Existing: skill ID guard --------------------------------------------
    if ALEXA_SKILL_ID:
        app_id = (
            (body_json.get("session") or {}).get("application", {}).get("applicationId")
            or (body_json.get("request") or {}).get("skillId")
            or ""
        )
        if not app_id and require_signature:
            raise HTTPException(status_code=403, detail="Missing Alexa skill ID")
        if app_id and not hmac.compare_digest(str(app_id), ALEXA_SKILL_ID):
            logger.warning("Alexa skill ID mismatch: %r", app_id)
            raise HTTPException(status_code=403, detail="Unexpected skill ID")
    elif require_signature:
        raise HTTPException(status_code=503, detail="Alexa skill ID is not configured on the server")

    # -- Existing: rate limiting ---------------------------------------------
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


# FAULT 4 FIX: dispatch_nlu_action is re-exported from the circular-import-
# free intermediary module app.alexa_dispatch.  The definition that previously
# lived here created a mcp_server <-> alexa_skill circular dependency.
from app.alexa_dispatch import dispatch_nlu_action  # noqa: E402


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

    required_fields = {
        "audit_repository": ("repo",),
        "audit_code": ("source_code",),
        "audit_and_score": ("source_code",),
        "calculate_sci": (
            "energy_joules",
            "duration_seconds",
            "functional_unit",
            "zone",
        ),
        "refactor_code": ("source_code",),
        "explain_score": ("green_score",),
        "push_green_fix": ("repo", "refactored_code"),
        "create_pull_request": ("repo", "head_branch"),
        "get_grid_intensity": ("zone",),
        "dynamic_analyze": ("repo", "grid_intensity"),
        "evaluate_sla": ("total_joules", "green_score", "sci_gco2e"),
    }
    missing_fields = [
        field
        for field in required_fields.get(tool, ())
        if payload.get(field) is None or payload.get(field) == ""
    ]
    if missing_fields:
        required = ", ".join(field.replace("_", " ") for field in missing_fields)
        return {
            "status": "error",
            "data": {
                "reason": (
                    f"This voice request is missing {required}. Provide the real "
                    "repository, source code, or measurement in the GreenCode dashboard."
                )
            },
        }
    if tool == "compare_regions" and len(set(payload.get("zones", []))) < 2:
        return {
            "status": "error",
            "data": {
                "reason": (
                    "Name two real regions to compare, for example Ireland and Virginia."
                )
            },
        }
    if tool == "scope_inventory":
        return {
            "status": "error",
            "data": {
                "reason": (
                    "A Scope 1-3 inventory needs your actual workload, infrastructure, "
                    "and usage inputs. Enter them in the GreenCode dashboard; Alexa "
                    "will not assume sample values."
                )
            },
        }
    if tool in {"push_green_fix", "create_pull_request"} and not github_token:
        return {
            "status": "error",
            "data": {
                "reason": (
                    "This request has no GitHub credential. Connect GitHub in the "
                    "GreenCode dashboard before asking for a repository change."
                )
            },
        }
    if tool == "measure_energy":
        return {
            "status": "error",
            "data": {
                "reason": (
                    "Alexa cannot measure a specific running workload from this voice "
                    "request. Use the GreenCode Profiler to select and measure a process."
                )
            },
        }
    if tool == "deploy_production":
        return {
            "status": "error",
            "data": {
                "reason": (
                    "No production deployment action is configured for Alexa. "
                    "Use the project's deployment workflow instead."
                )
            },
        }

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
                total_joules=float(payload["total_joules"]),
                green_score=float(payload["green_score"]),
                sci_gco2e=float(payload["sci_gco2e"]),
                config_path=payload.get("config_path"),
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
                repo=str(payload["repo"]),
                ref=str(payload.get("ref", "")),
                grid_intensity=float(payload["grid_intensity"]),
                functional_unit=float(payload.get("functional_unit", 1.0) or 1.0),
                timeout_sec=float(payload.get("timeout_sec", 60.0) or 60.0),
                github_token=github_token,
            )

        from app import mcp_server

        if tool == "audit_repository":
            return mcp_server.audit_repository(
                repo=payload.get("repo", ""),
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
            return mcp_server.get_grid_intensity(zone=payload["zone"])
        if tool == "compare_regions":
            return mcp_server.compare_regions(zones=payload["zones"])
        if tool == "calculate_sci":
            return mcp_server.calculate_sci(
                energy_joules=payload["energy_joules"],
                duration_seconds=payload.get("duration_seconds", 1.0),
                functional_unit=payload.get("functional_unit", 1.0),
                zone=payload.get("zone", "US-CAL-CISO"),
            )
        if tool == "refactor_code":
            return mcp_server.refactor_code(
                source_code=payload.get("source_code", ""),
                language=payload.get("language", "python"),
            )
        if tool == "explain_score":
            return mcp_server.explain_score(
                green_score=payload["green_score"],
                zone=payload.get("zone", "US-CAL-CISO"),
                measurement_method=payload.get("measurement_method", "model"),
                functional_unit=payload.get("functional_unit", 1.0),
            )

        if tool == "push_green_fix":
            from app.github_client import push_green_fix as gh_push
            return gh_push(
                repo=payload["repo"],
                file_path=payload.get("file_path", "refactored.py"),
                refactored_code=payload.get("refactored_code", ""),
                branch=payload.get("branch", "green-fix"),
                base_branch=payload.get("base_branch", "main"),
                token=github_token,
            )

        if tool == "create_pull_request":
            from app.github_client import create_pull_request as gh_pr
            return gh_pr(
                repo=payload["repo"],
                title=payload.get("title", "GreenCode: automated refactor"),
                head_branch=payload.get("head_branch", "green-fix"),
                base_branch=payload.get("base_branch", "main"),
                body=payload.get("body", ""),
                token=github_token,
            )

        return {
            "status": "error",
            "data": {"reason": f"Unknown GreenCode tool: {tool}"},
        }
    except Exception as exc:  # noqa: BLE001 - reported back to the speaker
        logger.exception("GreenCode tool %s failed", tool)
        return {"status": "error", "data": {"reason": f"{type(exc).__name__}: {exc}"}}



# ------------------------------------------------------------------ webhook -


@router.post("/skill", summary="Alexa Custom Skill webhook")
@router.post("/alexa/skill", summary="Alexa Custom Skill webhook")
@router.post("/api/voice/alexa/ask", summary="Local browser voice assistant")
async def alexa_skill(
    request: Request,
    x_greencode_org: Optional[str] = Header(default=None, alias="x-greencode-org"),
    authorization: Optional[str] = Header(default=None, alias="authorization"),
    x_github_token: Optional[str] = Header(default=None, alias="x-github-token"),
) -> JSONResponse:
    body = await request.body()
    _verify_alexa_request(
        dict(request.headers),
        body,
        require_signature=request.url.path != "/api/voice/alexa/ask",
    )

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

    github_token = x_github_token.strip() if x_github_token else None

    command = MAPPER.map(utterance)
    if command.tool == "audit_diff":
        if user_id is None:
            result = {
                "status": "error",
                "data": {
                    "reason": (
                        "A Green Release Briefing requires a signed-in GreenCode "
                        "dashboard session. Sign in and connect GitHub first."
                    )
                },
            }
        elif not github_token:
            result = {
                "status": "error",
                "data": {
                    "reason": (
                        "A Green Release Briefing needs your GitHub connection. "
                        "Connect GitHub in the dashboard, then try again."
                    )
                },
            }
        else:
            repo = command.payload.get("repo") or session_attrs.get("active_repo")
            if not isinstance(repo, str) or not re.fullmatch(
                r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo.strip()
            ):
                result = {
                    "status": "error",
                    "data": {
                        "reason": (
                            "I need a GitHub repository. Run a repository scan in "
                            "the dashboard first, then ask me to audit a pull request."
                        )
                    },
                }
            elif not command.payload.get("pr_number"):
                result = {
                    "status": "error",
                    "data": {
                        "reason": (
                            "Please include the pull request number, for example "
                            "'audit pull request 42'."
                        )
                    },
                }
            else:
                command.payload["repo"] = repo.strip()
                result = _call_greencode_tool(
                    command,
                    org_id=org_id,
                    user_id=user_id,
                    github_token=github_token,
                )
    else:
        result = _call_greencode_tool(
            command, org_id=org_id, user_id=user_id, github_token=github_token
        )
    logger.info(
        "Alexa command: intent=%s utterance=%r tool=%s confidence=%.2f fallback=%s",
        intent_name, utterance, command.tool, command.confidence, command.fallback,
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

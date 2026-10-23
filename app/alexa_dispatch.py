"""Alexa NLU dispatch intermediary.

Breaks the circular import between app.mcp_server and app.alexa_skill.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("greencode.alexa.dispatch")

_NLU_ACTION_TOOLS = frozenset({"audit_diff", "evaluate_sla", "scope_inventory", "audit_history", "dynamic_analyze"})


def dispatch_nlu_action(utterance: str, github_token=None, user_id=None):
    """Run one of the five NLU-mapped dashboard actions for utterance.

    Returns None when the utterance does not map to one of the five
    dashboard-backed actions.  Otherwise returns {"tool": name, "result": envelope}.
    """
    from app.alexa_nlp import MAPPER
    from app.alexa_actions import audit_diff, audit_history, dynamic_analyze, evaluate_sla

    command = MAPPER.map(utterance)
    if command.tool not in _NLU_ACTION_TOOLS or command.fallback:
        return None

    payload = dict(command.payload)
    tool = command.tool

    try:
        if tool == "audit_diff":
            result = audit_diff(diff_text=str(payload.get("diff_text", "")), repo=str(payload.get("repo", "")), pr_number=payload.get("pr_number"), github_token=github_token)
        elif tool == "evaluate_sla":
            required = ("total_joules", "green_score", "sci_gco2e")
            missing = [field for field in required if payload.get(field) is None]
            if missing:
                fields = ", ".join(field.replace("_", " ") for field in missing)
                result = {
                    "status": "error",
                    "data": {
                        "reason": (
                            f"An SLA check needs actual {fields}. Run the measurement "
                            "and SLA check in the GreenCode dashboard."
                        )
                    },
                }
            else:
                result = evaluate_sla(
                    total_joules=float(payload["total_joules"]),
                    green_score=float(payload["green_score"]),
                    sci_gco2e=float(payload["sci_gco2e"]),
                    config_path=payload.get("config_path"),
                )
        elif tool == "scope_inventory":
            result = {
                "status": "error",
                "data": {
                    "reason": (
                        "A Scope 1-3 inventory needs actual workload, infrastructure, "
                        "and usage data. Enter those inputs in the GreenCode dashboard; "
                        "Alexa will not assume sample values."
                    )
                },
            }
        elif tool == "audit_history":
            if user_id is None:
                result = {
                    "status": "error",
                    "data": {
                        "reason": (
                            "Audit history is available only in the authenticated "
                            "GreenCode dashboard."
                        )
                    },
                }
            else:
                result = audit_history(
                    limit=int(payload.get("limit", 5) or 5),
                    offset=int(payload.get("offset", 0) or 0),
                    user_id=user_id,
                )
        elif tool == "dynamic_analyze":
            required = ("repo", "grid_intensity", "functional_unit")
            missing = [field for field in required if payload.get(field) is None or payload.get(field) == ""]
            if missing:
                fields = ", ".join(field.replace("_", " ") for field in missing)
                result = {
                    "status": "error",
                    "data": {
                        "reason": (
                            f"Dynamic analysis needs an explicit repository, grid "
                            f"intensity, and functional unit; missing {fields}."
                        )
                    },
                }
            else:
                result = dynamic_analyze(
                    repo=str(payload["repo"]),
                    ref=str(payload.get("ref", "")),
                    grid_intensity=float(payload["grid_intensity"]),
                    functional_unit=float(payload["functional_unit"]),
                    timeout_sec=float(payload.get("timeout_sec", 60.0) or 60.0),
                    github_token=github_token,
                )
        else:
            return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("NLU dispatch action %s failed", tool)
        result = {"status": "error", "data": {"reason": f"{type(exc).__name__}: {exc}"}}

    return {"tool": tool, "result": result}

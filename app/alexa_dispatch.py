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
    from app.alexa_actions import audit_diff, audit_history, dynamic_analyze, evaluate_sla, scope_inventory

    command = MAPPER.map(utterance)
    if command.tool not in _NLU_ACTION_TOOLS or command.fallback:
        return None

    payload = dict(command.payload)
    tool = command.tool

    try:
        if tool == "audit_diff":
            result = audit_diff(diff_text=str(payload.get("diff_text", "")), repo=str(payload.get("repo", "")), pr_number=payload.get("pr_number"), github_token=github_token)
        elif tool == "evaluate_sla":
            result = evaluate_sla(total_joules=float(payload.get("total_joules", 0.0) or 0.0), green_score=float(payload.get("green_score", 0.0) or 0.0), sci_gco2e=float(payload.get("sci_gco2e", 0.0) or 0.0), config_path=payload.get("config_path"))
        elif tool == "scope_inventory":
            result = scope_inventory(energy_joules=float(payload.get("energy_joules", 3600.0) or 3600.0), duration_seconds=float(payload.get("duration_seconds", 1.0) or 1.0), grid_intensity_gco2_per_kwh=float(payload.get("grid_intensity_gco2_per_kwh", 200.0) or 200.0), runs_per_year=int(payload.get("runs_per_year", 10000) or 10000), team_size=int(payload.get("team_size", 5) or 5), dev_hours=float(payload.get("dev_hours", 160.0) or 160.0), cloud_provider=str(payload.get("cloud_provider", "aws")), vcpu_count=int(payload.get("vcpu_count", 2) or 2), memory_gb=float(payload.get("memory_gb", 4.0) or 4.0), data_transfer_gb=float(payload.get("data_transfer_gb", 0.05) or 0.05), grid_zone=str(payload.get("grid_zone", "US-CAL-CISO")), renewable_rec_pct=float(payload.get("renewable_rec_pct", 0.0) or 0.0))
        elif tool == "audit_history":
            result = audit_history(limit=int(payload.get("limit", 5) or 5), offset=int(payload.get("offset", 0) or 0), user_id=user_id)
        elif tool == "dynamic_analyze":
            result = dynamic_analyze(repo=str(payload.get("repo", "")), ref=str(payload.get("ref", "")), grid_intensity=float(payload.get("grid_intensity", 380.0) or 380.0), functional_unit=float(payload.get("functional_unit", 1.0) or 1.0), timeout_sec=float(payload.get("timeout_sec", 60.0) or 60.0), github_token=github_token)
        else:
            return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("NLU dispatch action %s failed", tool)
        result = {"status": "error", "data": {"reason": f"{type(exc).__name__}: {exc}"}}

    return {"tool": tool, "result": result}

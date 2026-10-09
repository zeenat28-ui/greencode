"""GitHub PR Sticky Comment Integration.

Posts and updates automated sticky markdown summaries on Pull Requests,
visualizing energy regression deltas, cost differences ($ USD/yr), and merge blocking decisions.
"""

import json
import logging
import os
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

logger = logging.getLogger("greencode.github.pr_comment")

GATE_MARKER = "<!-- greencode-energy-gate -->"


def format_pr_sticky_comment(diff_result: Dict[str, Any], repo_slug: str, pr_number: int) -> str:
    """Format full GitHub Markdown sticky comment with badges and breakdown table."""
    decision = diff_result.get("verdict", "APPROVED")
    is_blocked = diff_result.get("is_blocked", False)
    energy_delta_pct = diff_result.get("energy_delta_pct", 0.0)
    annual_cost_usd = diff_result.get("annual_cost_delta_usd", 0.0)
    annual_carbon_kg = diff_result.get("annual_carbon_delta_kg", 0.0)
    base_score = diff_result.get("base_green_score", 100.0)
    head_score = diff_result.get("head_green_score", 100.0)

    badge = "🟢 **PASSED - GREEN VERIFIED**"
    if is_blocked:
        badge = "🔴 **FAILED - MERGE BLOCKED BY GREEN POLICY**"
    elif decision == "WARN" or decision == "WARNING":
        badge = "🟡 **WARNING - EFFICIENCY REGRESSION DETECTED**"

    cost_sign = "+" if annual_cost_usd >= 0 else "-"
    energy_sign = "+" if energy_delta_pct >= 0 else ""

    markdown = f"""{GATE_MARKER}
## 🌱 GreenCode Energy & Carbon Gatekeeper

### {badge}

| Metric | Base Branch | Pull Request | Impact (Δ) |
| :--- | :--- | :--- | :--- |
| **Green Code Score** | `{base_score:.1f}` | `{head_score:.1f}` | `{head_score - base_score:+.1f} pts` |
| **Execution Energy** | Reference Baseline | Current PR Candidate | **`{energy_sign}{energy_delta_pct:.2f}%`** |
| **Projected Cloud Infrastructure Cost** | Baseline Rate | Projected Run-rate | **`{cost_sign}${abs(annual_cost_usd):,.2f} / yr`** |
| **Scope 2 Carbon Impact** | Baseline Rate | Projected Emissions | **`{annual_carbon_kg:+.2f} kg CO2e / yr`** |

"""
    if is_blocked:
        markdown += f"""\n> [!CAUTION]
> **Action Required:** Energy regression of **`{energy_delta_pct:.1f}%`** exceeds the project policy limit. 
> To unblock merge:
> 1. Hoist allocations and non-blocking I/O outside loops.
> 2. Run `greencode optimize` or query GreenCode MCP server for verified AST refactorings.
"""
    else:
        markdown += "\n> [!NOTE]\n> PR passes all organizational energy, cost, and carbon compliance guardrails.\n"

    markdown += f"\n*Audited by GreenCode Gatekeeper for `{repo_slug}#{pr_number}`*"
    return markdown


def post_github_pr_comment(
    repo_slug: str,
    pr_number: int,
    comment_body: str,
    github_token: Optional[str] = None,
) -> Dict[str, Any]:
    """Post or update sticky PR comment via GitHub REST API."""
    token = github_token or os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.info("No GITHUB_TOKEN configured; skipping remote comment dispatch.")
        return {"status": "LOCAL_MOCK", "body": comment_body}

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GreenCode-Gatekeeper",
        "Content-Type": "application/json",
    }

    comments_url = f"https://api.github.com/repos/{repo_slug}/issues/{pr_number}/comments"

    # Step 1: Check for existing sticky comment to update
    existing_comment_id = None
    try:
        req = urllib.request.Request(comments_url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            comments = json.loads(resp.read().decode("utf-8"))
            for c in comments:
                if GATE_MARKER in c.get("body", ""):
                    existing_comment_id = c["id"]
                    break
    except Exception as exc:
        logger.warning("Error querying existing PR comments: %s", exc)

    if existing_comment_id:
        try:
            patch_url = f"https://api.github.com/repos/{repo_slug}/issues/comments/{existing_comment_id}"
            payload = json.dumps({"body": comment_body}).encode("utf-8")
            patch_req = urllib.request.Request(
                patch_url,
                data=payload,
                headers=headers,
                method="PATCH",
            )
            with urllib.request.urlopen(patch_req, timeout=10.0) as patch_resp:
                return {"status": "UPDATED", "comment_id": existing_comment_id}
        except Exception as exc:
            logger.warning("Failed to update existing comment: %s", exc)

    # Step 2: Post new comment
    try:
        post_req = urllib.request.Request(
            comments_url,
            data=json.dumps({"body": comment_body}).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(post_req, timeout=10.0) as post_resp:
            result = json.loads(post_resp.read().decode("utf-8"))
            return {"status": "CREATED", "comment_id": result.get("id")}
    except Exception as exc:
        logger.error("Failed to post GitHub PR comment: %s", exc)
        return {"status": "ERROR", "error": str(exc)}


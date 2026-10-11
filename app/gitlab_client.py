"""GitLab API v4 Merge Request Carbon Gate & Automated Suggestion Client.

Supports GitLab.com and self-hosted GitLab instances, generating sticky Merge
Request carbon audit notes, GitLab `suggestion:-0+0` 1-click commit blocks,
and webhook event processing.
"""

from typing import Any, Dict, List, Optional
import urllib.parse
import httpx

from app.optimizer import _synthesize_green_code, generate_unified_diff

STICKY_GITLAB_MARKER = "<!-- greencode-gitlab-mr-comment -->"


def generate_gitlab_suggestion_block(
    refactored_code: str,
    lines_above: int = 0,
    lines_below: int = 0,
) -> str:
    """Format refactored code as a GitLab Merge Request 1-click suggestion block."""
    cleaned = (refactored_code or "").strip("\r\n")
    return f"```suggestion:-{max(0, int(lines_above))}+{max(0, int(lines_below))}\n{cleaned}\n```"


def _format_violation_row(idx: int, v: Dict[str, Any]) -> str:
    rel = v.get("relative_path") or v.get("file_path") or "code.py"
    line_no = v.get("line_number", 1)
    sev = v.get("severity", "MEDIUM")
    title = v.get("title", v.get("violation_type", "Anomaly"))
    ded = v.get("deduction", 0.0)
    return f"| {idx} | `{sev}` | `{rel}:{line_no}` | {title} | `-{ded}` |"


def _format_violation_patch(v: Dict[str, Any]) -> str:
    rel = v.get("relative_path") or v.get("file_path") or "code.py"
    vtype = str(v.get("violation_type", "INEFFICIENT_LOOP"))
    lang = str(v.get("language", "python"))
    snippet = str(v.get("snippet") or "")
    synth = _synthesize_green_code(snippet or str(v.get("title", "")), vtype, language_id=lang)
    refactored = str(synth.get("refactored_code") or "")
    diff_patch = generate_unified_diff(snippet or "# original", refactored, file_path=str(rel))
    span = max(0, int(v.get("span_lines", 1)) - 1)
    gl_suggestion = generate_gitlab_suggestion_block(refactored, lines_above=0, lines_below=span)
    return (
        f"#### `{rel}` (Line {v.get('line_number', 1)}) - {v.get('title', vtype)}\n"
        f"**Guidance:** {v.get('suggested_fix', synth.get('explanation', ''))}\n\n"
        f"```diff\n{diff_patch.strip()}\n```\n\n"
        f"**GitLab 1-Click Merge Request Suggestion:**\n{gl_suggestion}"
    )


def build_gitlab_mr_carbon_comment(
    scan_result: Dict[str, Any],
    threshold: float = 75.0,
    zone: str = "US-CAL-CISO",
) -> str:
    """Build a GitLab Merge Request sticky carbon gate markdown comment."""
    score = float(scan_result.get("green_score", 100.0))
    violations: List[Dict[str, Any]] = list(scan_result.get("violations", []))
    passed = score >= threshold
    status_label = "PASSED" if passed else "BLOCKED (Score Below Threshold)"

    sections: List[str] = [
        STICKY_GITLAB_MARKER,
        "## GreenCode Merge Request Carbon & FinOps Gate",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| **Gate Verdict** | **{status_label}** |",
        f"| **Green Score** | `{score} / 100.0` (Minimum Required: `{threshold}`) |",
        f"| **Violations Detected** | `{len(violations)}` |",
        f"| **Grid Zone** | `{zone}` |",
        "",
    ]

    if violations:
        sections.append("### Detected Energy & FinOps Findings")
        sections.append("| # | Severity | Location | Finding | Deduction |")
        sections.append("| :--- | :--- | :--- | :--- | :--- |")
        rows = [_format_violation_row(i, v) for i, v in enumerate(violations[:10], 1)]
        sections.extend(rows)
        sections.append("")
        sections.append("### Deterministic Autofix Patches & GitLab Suggestions")
        patches = [_format_violation_patch(v) for v in violations[:3]]
        sections.extend(patches)
    else:
        sections.append("Zero static energy or FinOps violations detected in this Merge Request.")

    return "\n".join(sections)


def post_gitlab_mr_comment(
    project_id: str,
    mr_iid: int,
    scan_result: Dict[str, Any],
    gitlab_token: Optional[str] = None,
    gitlab_url: str = "https://gitlab.com",
    threshold: float = 75.0,
    zone: str = "US-CAL-CISO",
) -> Dict[str, Any]:
    """Post a carbon gate comment to a GitLab Merge Request via GitLab REST API v4."""
    body_md = build_gitlab_mr_carbon_comment(scan_result, threshold=threshold, zone=zone)
    if not gitlab_token:
        return {
            "posted": False,
            "mode": "dry_run_preview",
            "project_id": project_id,
            "mr_iid": mr_iid,
            "markdown": body_md,
        }

    encoded_proj = urllib.parse.quote(str(project_id), safe="")
    base = gitlab_url.rstrip("/")
    notes_url = f"{base}/api/v4/projects/{encoded_proj}/merge_requests/{int(mr_iid)}/notes"
    headers = {"PRIVATE-TOKEN": gitlab_token, "Content-Type": "application/json"}

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(notes_url, headers=headers, json={"body": body_md})
        resp.raise_for_status()
        note_data = resp.json()

    return {
        "posted": True,
        "mode": "gitlab_api_v4",
        "project_id": project_id,
        "mr_iid": mr_iid,
        "note_id": note_data.get("id"),
        "markdown": body_md,
    }

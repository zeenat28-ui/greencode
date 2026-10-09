"""Provider-neutral audit intelligence: repository context and remediation planning.

Replaces the previous vendor-locked reporting layer. Nothing here depends on a
specific model provider; every field is computed deterministically from the
scan results, so the output is identical on every run.

What this adds over the raw violation list:
- Violations grouped by root cause, because 40 findings across 6 rule types is
  one architectural problem, not 40 separate bugs.
- A ranked, deduplicated remediation plan ordered by impact against effort.
- Explicit effort and risk ratings per step, which is the question an
  engineering lead actually needs answered before merging.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

# Each rule family gets a remediation theme, an effort class and a risk rating.
# Risk means "how likely is this change to alter behaviour", which is what
# determines whether a fix can be merged without a full regression pass.
RULE_PLAYBOOK: Dict[str, Dict[str, Any]] = {
    "QUADRATIC_STRING": {
        "theme": "Algorithmic complexity",
        "action": "Replace repeated string concatenation in a loop with a list "
                  "plus ''.join(), reducing allocation from O(n^2) to O(n).",
        "effort": "low", "risk": "low", "impact_weight": 0.9,
    },
    "NESTED_LOOP": {
        "theme": "Algorithmic complexity",
        "action": "Collapse the nested iteration into a single pass, or precompute "
                  "a lookup structure so the inner scan is eliminated.",
        "effort": "medium", "risk": "medium", "impact_weight": 0.85,
    },
    "ITERATIVE_APPEND": {
        "theme": "Allocation pressure",
        "action": "Hoist the accumulator out of the loop and append in place, or use "
                  "a comprehension, avoiding repeated list reallocation.",
        "effort": "low", "risk": "low", "impact_weight": 0.6,
    },
    "INEFFICIENT_LOOP": {
        "theme": "Algorithmic complexity",
        "action": "Hoist invariants out of the loop body and avoid repeated calls "
                  "or attribute lookups inside the hot path.",
        "effort": "low", "risk": "low", "impact_weight": 0.65,
    },
    "LARGE_MEMORY_FOOTPRINT": {
        "theme": "Memory efficiency",
        "action": "Stream or chunk the data instead of materialising it all at "
                  "once; prefer generators and iterators.",
        "effort": "medium", "risk": "medium", "impact_weight": 0.8,
    },
    "BLOCKING_CALL_IN_LOOP": {
        "theme": "I/O and concurrency",
        "action": "Hoist the call out of the loop, or batch the calls, so the "
                  "expensive operation runs once per batch rather than per item.",
        "effort": "medium", "risk": "medium", "impact_weight": 0.75,
    },
    "MISSING_CONNECTION_POOL": {
        "theme": "I/O and concurrency",
        "action": "Reuse a single client/session across calls so connections and "
                  "TLS handshakes are not rebuilt per request.",
        "effort": "low", "risk": "low", "impact_weight": 0.7,
    },
    "BATCH_MATRIX_MULTIPLICATION": {
        "theme": "Algorithmic complexity",
        "action": "Use a single vectorised matrix multiply instead of repeated "
                  "per-row multiplications.",
        "effort": "low", "risk": "low", "impact_weight": 0.8,
    },
    "IDLE_GPU_GAP": {
        "theme": "Hardware utilisation",
        "action": "Reduce idle gaps between GPU batches by pipelining work, so the "
                  "accelerator stays saturated instead of powering down.",
        "effort": "high", "risk": "high", "impact_weight": 0.95,
    },
}

_DEFAULT_PLAYBOOK = {
    "theme": "General efficiency",
    "action": "Review this site and apply the documented remediation guidance.",
    "effort": "low", "risk": "low", "impact_weight": 0.5,
}

_EFFORT_RANK = {"low": 1, "medium": 2, "high": 3}
_EFFORT_DAYS = {"low": 0.25, "medium": 1.0, "high": 3.0}


def _playbook_for(violation_type: str) -> Dict[str, Any]:
    return RULE_PLAYBOOK.get(str(violation_type or "").upper(), _DEFAULT_PLAYBOOK)


def analyze_repository_context(scan_result: Dict[str, Any]) -> Dict[str, Any]:
    """Summarise a scan deterministically.

    A pure function of the scan output, so two runs over the same commit
    produce byte-identical results.
    """
    violations = scan_result.get("violations") or []
    breakdown: Dict[str, int] = defaultdict(int)
    files_hit: set = set()
    lines_hit: set = set()

    for v in violations:
        breakdown[v.get("violation_type", "UNKNOWN")] += 1
        path = v.get("file") or v.get("path")
        if path:
            files_hit.add(path)
        line = v.get("line")
        if isinstance(line, int):
            lines_hit.add(line)

    total_files = scan_result.get("total_files") or 0
    total_lines = scan_result.get("total_lines") or 0

    themes: Dict[str, Dict[str, Any]] = {}
    for vtype, count in breakdown.items():
        pb = _playbook_for(vtype)
        entry = themes.setdefault(
            pb["theme"], {"count": 0, "rules": [], "weighted_impact": 0.0}
        )
        entry["count"] += count
        entry["rules"].append(vtype)
        entry["weighted_impact"] += count * pb["impact_weight"]

    ranked = sorted(themes.items(), key=lambda kv: kv[1]["weighted_impact"], reverse=True)

    return {
        "repository": scan_result.get("repo_path", ""),
        "total_files": total_files,
        "total_lines": total_lines,
        "green_score": scan_result.get("green_score", 100.0),
        "total_violations": len(violations),
        "files_with_violations": len(files_hit),
        "violation_themes": [
            {
                "theme": name,
                "count": d["count"],
                "rules": sorted(d["rules"]),
                "weighted_impact": round(d["weighted_impact"], 2),
            }
            for name, d in ranked
        ],
        "concentration": {
            "pct_files_affected": round(
                (len(files_hit) / total_files * 100.0) if total_files else 0.0, 2
            ),
            "pct_lines_affected": round(
                (len(lines_hit) / total_lines * 100.0) if total_lines else 0.0, 2
            ),
        },
    }


def build_remediation_plan(scan_result: Dict[str, Any]) -> Dict[str, Any]:
    """Rank remediation work by impact against effort, grouped by root cause.

    Returns a payload shaped for the dashboard: a deterministic context
    summary plus a ranked plan where each step names the files it touches and
    carries an effort and risk rating.
    """
    context = analyze_repository_context(scan_result)
    violations = scan_result.get("violations") or []

    # Group findings by rule so one plan step covers every occurrence of a fix.
    by_rule: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for v in violations:
        by_rule[v.get("violation_type", "UNKNOWN")].append(v)

    steps: List[Dict[str, Any]] = []
    for vtype, items in by_rule.items():
        pb = _playbook_for(vtype)
        raw_files = list({(i.get("file") or i.get("path") or "") for i in items} - {""})
        effort, risk = pb["effort"], pb["risk"]
        # Priority normalises occurrence count against the cost of doing the
        # work, so a high-volume low-effort fix outranks a rare high-effort one.
        priority = (len(items) * pb["impact_weight"]) / _EFFORT_RANK[effort]
        steps.append(
            {
                "violation_type": vtype,
                "theme": pb["theme"],
                "occurrences": len(items),
                "file_count": len(raw_files),
                "files": raw_files[:20],
                "action": pb["action"],
                "effort": effort,
                "risk": risk,
                "priority_score": round(priority, 3),
                "sample_lines": [
                    {
                        "file": i.get("file") or i.get("path") or "",
                        "line": i.get("line"),
                        "snippet": (i.get("snippet") or "")[:200],
                    }
                    for i in items[:5]
                ],
            }
        )

    steps.sort(key=lambda s: s["priority_score"], reverse=True)

    total_occurrences = sum(s["occurrences"] for s in steps)
    quick_wins = [s for s in steps if s["effort"] == "low" and s["risk"] == "low"]

    return {
        "context": context,
        "plan": {
            "steps": steps,
            "step_count": len(steps),
            "total_occurrences": total_occurrences,
            "quick_wins": len(quick_wins),
            "quick_win_occurrences": sum(s["occurrences"] for s in quick_wins),
            "estimated_effort": _estimate_effort(steps),
        },
        "breakdown": scan_result.get("violation_breakdown") or {},
    }


def _estimate_effort(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rough engineer-day estimate from per-step effort class and occurrence count."""
    days = 0.0
    for s in steps:
        base = _EFFORT_DAYS.get(s["effort"], 0.5)
        # Diminishing returns: the first few fixes in a file carry most of the
        # work; later ones repeat the same edit and are much cheaper.
        days += base * (1 + 0.25 * max(0, s["occurrences"] - 1))

    if days <= 0:
        band = "none"
    elif days < 1:
        band = "under a day"
    elif days < 3:
        band = "1-3 days"
    elif days < 8:
        band = "about a week"
    else:
        band = "more than a week"

    return {"engineer_days": round(days, 2), "band": band}




"""Natural Language Processor for Alexa voice commands.

Maps free-form spoken utterances from a boss to GreenCode MCP tools and REST
endpoints. No external NLP dependency - uses compiled regex + keyword scoring
so it works offline and sub-50ms on a Lambda cold start.

Design goals:
- A boss can say ANYTHING reasonable, not just rigid sample phrases.
- Every mapping returns (tool_name, payload, speakable_summary, confidence).
- Unknown commands fall back to a helpful suggestion list instead of dying.
- Multi-tenant: org_id / user_id flow through from the JWT or request header.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


_PATTERNS: List[Tuple[re.Pattern[str], str, Any, int]] = []


def _pat(regex: str, tool: str, payload_fn=None, priority: int = 0) -> None:
    """Register one utterance pattern.

    ``priority`` breaks ties between patterns that both match: a specific
    command ("audit pull request 42") must win over the generic
    ("audit ... repository") even when the generic one matches more text.
    """
    _PATTERNS.append(
        (re.compile(regex, re.IGNORECASE), tool, payload_fn or (lambda m: {}), priority)
    )


# 1. REPOSITORY AUDIT -------------------------------------------------------
_pat(
    r"\b(audit|scan|check|review|analyse|analyze)\b.*\b(repository|repo|github|codebase)\b",
    "audit_repository",
    lambda m: {"repo": _extract_repo(m.group(0)) or "owner/repo", "branch": "main"},
)
_pat(
    r"\b(audit|scan|check)\b.*\b(my\s+)?(code|repo|repository)\b",
    "audit_repository",
    lambda m: {"repo": _extract_repo(m.group(0)) or "owner/repo", "branch": "main"},
)
_pat(
    r"\b(green score|eco score|carbon score)\b.*\b(of|for|my)\b.*\b(repository|repo|code)\b",
    "audit_repository",
    lambda m: {"repo": _extract_repo(m.group(0)) or "owner/repo", "branch": "main"},
)

# 2. SNIPPET / CODE AUDIT ---------------------------------------------------
_pat(
    r"\b(audit|scan|check|review)\b.*\b(snippet|function|this code|this function)\b",
    "audit_code",
    lambda m: {"source_code": _extract_snippet(m.group(0)), "language": "python"},
)
_pat(
    r"\b(nested loop|quadratic|energy waste|anti.?pattern|carbon anti.?pattern)\b",
    "audit_code",
    lambda m: {"source_code": m.group(0), "language": "python"},
)

# 3. END-TO-END AUDIT AND SCORE ---------------------------------------------
_pat(
    r"\b(audit and score|full audit|complete audit|end.to.end|green score)\b",
    "audit_and_score",
    lambda m: {
        "source_code": _extract_snippet(m.group(0)),
        "language": "python",
        "zone": "US-CAL-CISO",
        "functional_unit": 1.0,
        "duration_seconds": 1.0,
    },
)

# 4. GRID INTENSITY / REGION ------------------------------------------------
_pat(
    r"\b(grid|carbon intensity|cleanest|greenest|dirtiest)\b.*\b(region|zone|aws)\b",
    "get_grid_intensity",
    lambda m: {"zone": _extract_zone(m.string) or "US-CAL-CISO"},
)
_pat(
    r"\b(compare|which|should we run|where should)\b.*\b(region|zone|aws)\b",
    "compare_regions",
    lambda m: {"zones": _extract_zones(m.group(0)) or ["US-CAL-CISO", "IE"]},
)
_pat(
    r"\bcompare\b\s+(?:the\s+)?(?:carbon\s+)?(?:intensity\s+)?(?:of\s+)?(.+?)\s+(?:and|vs|versus|verses|or)\s+(.+)",
    "compare_regions",
    lambda m: {"zones": _extract_zones(m.group(1) + " " + m.group(2)) or ["US-CAL-CISO", "IE"]},
)
_pat(
    r"\b(what is the carbon intensity|how clean is the grid|grid intensity)\b",
    "get_grid_intensity",
    lambda m: {"zone": _extract_zone(m.string) or "US-CAL-CISO"},
)


_pat(
    r"\bcarbon intensity\b(?:\s+of)?\s+(.+)",
    "get_grid_intensity",
    lambda m: {"zone": _extract_zone(m.group(1)) or "US-CAL-CISO"},
)

# 5. SCI CALCULATION --------------------------------------------------------
_pat(
    r"\b(calculate sci|software carbon intensity|sci score|carbon intensity score)\b",
    "calculate_sci",
    lambda m: {
        "energy_joules": 1000.0,
        "duration_seconds": 60.0,
        "functional_unit": 1.0,
        "zone": "US-CAL-CISO",
    },
)

# 6. ENERGY MEASUREMENT -----------------------------------------------------
_pat(
    r"\b(measure energy|power draw|watts|joules|energy consumption|hardware reading)\b",
    "measure_energy",
    lambda m: {"cpu_percent": 50.0, "memory_mb": 512.0, "duration_seconds": 1.0},
)

# 7. REFACTOR / OPTIMIZE ----------------------------------------------------
_pat(
    r"\b(refactor|optimize|fix|improve|clean up|reduce energy|lower carbon)\b",
    "refactor_code",
    lambda m: {"source_code": _extract_snippet(m.group(0)), "language": "python"},
)

# 8. EXPLAIN SCORE ----------------------------------------------------------
_pat(
    r"\b(explain|why|breakdown|reason for)\b.*\b(score|grade|green|carbon)\b",
    "explain_score",
    lambda m: {
        "green_score": 75.0,
        "zone": "US-CAL-CISO",
        "measurement_method": "model",
        "functional_unit": 1.0,
    },
)

# 9. LIST / MY REPOSITORIES -------------------------------------------------
_pat(
    r"\b(my repos|list repos|show repositories|my repositories|all repos)\b",
    "list_repositories",
    lambda m: {},
)

# 10. BILLING / FINOPS ------------------------------------------------------
_pat(
    r"\b(billing|cost|finops|cloud cost|monthly spend|aws bill)\b",
    "reconcile_focus_billing",
    lambda m: {},
)


# 10.5. GITHUB PUSH & PULL REQUEST ------------------------------------------
_pat(
    r"\b(push to github|push code|push fix|commit code|push refactor|github push)\b",
    "push_green_fix",
    lambda m: {"repo": _extract_repo(m.string) or "owner/repo", "file_path": "refactored.py"},
)
_pat(
    r"\b(create pull request|open pr|make pr|create pr|pull request)\b",
    "create_pull_request",
    lambda m: {"repo": _extract_repo(m.string) or "owner/repo"},
)

# 10.6. DEPLOY TO PRODUCTION ------------------------------------------------
_pat(
    r"\b(deploy to production|deploy now|ship to prod|production deploy|deploy app)\b",
    "deploy_production",
    lambda m: {"environment": "production"},
)

# 10.7. PULL REQUEST DIFF AUDIT --------------------------------------------
# Priority 10 so "audit pull request 42" beats the generic repository audit.
_pat(
    r"\b(audit|check|scan|review)\b.*\b(pull request|merge request|pr)\b"
    r"(?:\s*(?:number\s*|#)?\s*(\d+))?",
    "audit_diff",
    lambda m: {
        "repo": _extract_repo(m.string) or "",
        "pr_number": int(m.group(3)) if m.group(3) else _extract_pr_number(m.string),
    },
    priority=10,
)
_pat(
    r"\b(audit|check|scan|review)\b.*\b(the\s+)?diff\b",
    "audit_diff",
    lambda m: {
        "repo": _extract_repo(m.string) or "",
        "pr_number": _extract_pr_number(m.string),
    },
    priority=10,
)

# 10.8. ENERGY SLA EVALUATION ------------------------------------------------
_pat(
    r"\b(sla|energy budget|budget policy|service level agreement)\b"
    r".*\b(check|evaluate|assess|does|pass|meets?|meet|violat|comply|compliant)",
    "evaluate_sla",
    lambda m: {
        "total_joules": _extract_number(m.string, ("joules", "joule")) or 0.0,
        "green_score": _extract_number(m.string, ("score",)) or 0.0,
        "sci_gco2e": _extract_number(m.string, ("sci",)) or 0.0,
    },
    priority=10,
)
_pat(
    r"\b(check|evaluate|assess|does|do|pass|meets?|meet|violat|comply|compliant)\b"
    r".*\b(sla|energy budget|budget policy|service level agreement)\b",
    "evaluate_sla",
    lambda m: {
        "total_joules": _extract_number(m.string, ("joules", "joule")) or 0.0,
        "green_score": _extract_number(m.string, ("score",)) or 0.0,
        "sci_gco2e": _extract_number(m.string, ("sci",)) or 0.0,
    },
    priority=10,
)

# 10.9. SCOPE 1-3 INVENTORY ---------------------------------------------------
_pat(
    r"\b(scope\s*(one|two|three|1|2|3)|ghg inventory|emissions inventory|"
    r"carbon inventory|scope inventory)\b",
    "scope_inventory",
    lambda m: {
        "grid_zone": _extract_zone(m.string) or "US-CAL-CISO",
        "grid_intensity_gco2_per_kwh": 200.0,
    },
    priority=10,
)

# 10.10. AUDIT HISTORY --------------------------------------------------------
_pat(
    r"\b(audit history|audit log|history of audits|my audits|recent audits|"
    r"past audits|previous audits|what have i audited)\b",
    "audit_history",
    lambda m: {"limit": 5, "offset": 0},
    priority=10,
)

# 10.11. DYNAMIC ANALYSIS -----------------------------------------------------
_pat(
    r"\b(dynamically|run it and see|run the repo|actually run|profile the repo|"
    r"dynamic analysis|dynamic profile|real world measurement)\b",
    "dynamic_analyze",
    lambda m: {"repo": _extract_repo(m.string) or ""},
    priority=10,
)

# 11. HELP / CAPABILITIES ---------------------------------------------------
_pat(
    r"\b(help|what can you do|capabilities|commands|how to use)\b",
    "help",
    lambda m: {},
)

@dataclass
class AlexaCommand:
    """A parsed voice command ready to dispatch to GreenCode."""

    tool: str
    payload: Dict[str, Any]
    summary: str
    confidence: float
    raw_utterance: str
    fallback: bool = False

_ZONE_ALIASES: Dict[str, str] = {
    "ireland": "IE", "eu-west-1": "IE", "frankfurt": "DE", "eu-central-1": "DE",
    "paris": "FR", "eu-west-3": "FR", "stockholm": "SE", "eu-north-1": "SE",
    "california": "US-CAL-CISO", "us-west-1": "US-CAL-CISO", "silicon valley": "US-CAL-CISO",
    "oregon": "US-NW-PACW", "us-west-2": "US-NW-PACW", "virginia": "US-MIDA-PJM",
    "us-east-1": "US-MIDA-PJM", "ohio": "US-EAST-2", "us-east-2": "US-EAST-2",
    "singapore": "SG", "ap-southeast-1": "SG", "tokyo": "JP-TK", "ap-northeast-1": "JP-TK",
    "sydney": "AU-NSW", "ap-southeast-2": "AU-NSW", "mumbai": "IN-WE",
    "ap-south-1": "IN-WE", "london": "GB", "eu-west-2": "GB",
}


def _extract_zone(text: str) -> Optional[str]:
    lowered = text.lower()
    for alias, zone in _ZONE_ALIASES.items():
        if alias in lowered:
            return zone
    m = re.search(r"\b([A-Z]{2}-[A-Z]+-\d+|[A-Z]{2})\b", text)
    if m:
        return m.group(1)
    return None


def _extract_zones(text: str) -> List[str]:
    found: List[str] = []
    lowered = text.lower()
    for alias, zone in _ZONE_ALIASES.items():
        if alias in lowered and zone not in found:
            found.append(zone)
    if len(found) < 2:
        tokens = re.findall(r"\b([A-Z]{2}-[A-Z]+-\d+|[A-Z]{2})\b", text)
        for t in tokens:
            if t not in found:
                found.append(t)
    if not found:
        found = ["US-CAL-CISO", "IE"]
    return found[:5]


# Compiled once at module level: a regex rebuilt inside a loop is one of the
# anti-patterns GreenCode itself audits for.
_NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")
_AFTER_NUMBER_RE = re.compile(r"\s*(?:is|of|=|:)?\s*(\d+(?:\.\d+)?)")
_PR_NUMBER_RE = re.compile(
    r"(?:#|pull request\s*|merge request\s*|pr\s*)(\d+)", re.IGNORECASE
)
_KEYWORD_RE_CACHE: Dict[str, re.Pattern[str]] = {}


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """Return the compiled "keyword or keywords" pattern for ``keyword``."""
    pattern = _KEYWORD_RE_CACHE.get(keyword)
    if pattern is None:
        pattern = re.compile(rf"\b{re.escape(keyword)}s?\b")
        _KEYWORD_RE_CACHE[keyword] = pattern
    return pattern


def _extract_number(text: str, keywords: Tuple[str, ...]) -> Optional[float]:
    """Find a number that sits next to one of ``keywords``.

    Handles both orders the boss might use: "1200 joules" and "joules 1200".
    Numbers written as words ("twelve hundred") are not supported; the
    number form is what a phone transcription produces most reliably.
    """
    lowered = text.lower()
    for keyword in keywords:
        for m in _keyword_pattern(keyword).finditer(lowered):
            before = lowered[max(0, m.start() - 24) : m.start()]
            after = lowered[m.end() : m.end() + 24]

            after_match = _AFTER_NUMBER_RE.match(after)
            if after_match:
                try:
                    return float(after_match.group(1))
                except ValueError:
                    pass

            before_matches = _NUMBER_RE.findall(before)
            if before_matches:
                try:
                    return float(before_matches[-1])
                except ValueError:
                    pass
    return None


def _extract_pr_number(text: str) -> Optional[int]:
    """Find a pull request number, either as "pr 42" / "pull request 42" / "#42"."""
    m = _PR_NUMBER_RE.search(text)
    if m:
        return int(m.group(1))
    return None


def _extract_repo(text: str) -> Optional[str]:
    m = re.search(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\b", text)
    if m:
        return m.group(1)
    m = re.search(
        r"\b(?:repo|repository|github)\s+(?:of|is|called|named)?\s+([A-Za-z0-9_.-]+)",
        text, re.IGNORECASE,
    )
    if m:
        return f"owner/{m.group(1)}"
    return None


def _extract_snippet(text: str) -> str:
    return (
        "def example(x):\n"
        "    total = 0\n"
        "    for i in range(x):\n"
        "        for j in range(x):\n"
        "            total += i * j\n"
        "    return total\n"
    )


class AlexaNLUMapper:
    """Map any spoken utterance to a GreenCode action."""

    def __init__(self) -> None:
        self._patterns = _PATTERNS

    def map(self, utterance: str) -> AlexaCommand:
        if not utterance or not utterance.strip():
            return self._fallback(
                utterance, "Empty command. Say: 'audit my repository' or 'what is my green score?'"
            )

        best: Optional[AlexaCommand] = None
        best_conf = 0.0
        best_priority = -1

        for pattern, tool, payload_fn, priority in self._patterns:
            m = pattern.search(utterance)
            if not m:
                continue
            conf = min(0.95, 0.6 + (len(m.group(0)) / max(len(utterance), 1)) * 0.35)
            # A higher-priority pattern always wins; within one priority the
            # better match (longer share of the utterance) wins.
            if priority > best_priority or (
                priority == best_priority and conf > best_conf
            ):
                best_priority = priority
                best_conf = conf
                best = AlexaCommand(
                    tool=tool,
                    payload=payload_fn(m),
                    summary=self._speakable(tool, payload_fn(m)),
                    confidence=conf,
                    raw_utterance=utterance,
                )

        if best is None:
            return self._fallback(utterance)

        # A specific (higher-priority) command is accepted on a slightly
        # weaker match than a generic one, because the generic patterns
        # would otherwise swallow it.
        threshold = 0.65 if best_priority <= 0 else 0.55
        if best_conf < threshold:
            return self._fallback(utterance)

        return best

    @staticmethod
    def _speakable(tool: str, payload: Dict[str, Any]) -> str:
        if tool == "audit_repository":
            return (
                f"Auditing repository {payload.get('repo', 'your repo')} "
                f"on branch {payload.get('branch', 'main')}."
            )
        if tool == "audit_code":
            return "Auditing your code snippet for energy anti-patterns."
        if tool == "audit_and_score":
            return "Running a full audit and energy score on your code."
        if tool == "get_grid_intensity":
            return (
                f"Checking grid carbon intensity for {payload.get('zone', 'your region')}."
            )
        if tool == "compare_regions":
            zones = ", ".join(payload.get("zones", []))
            return f"Comparing carbon intensity across {zones}."
        if tool == "calculate_sci":
            return "Calculating Software Carbon Intensity for your workload."
        if tool == "measure_energy":
            return "Measuring energy draw on this machine."
        if tool == "refactor_code":
            return "Refactoring your code to reduce energy consumption."
        if tool == "explain_score":
            return "Explaining your green score breakdown."
        if tool == "list_repositories":
            return "Listing your repositories."
        if tool == "reconcile_focus_billing":
            return "Reconciling your cloud billing with carbon data."
        if tool == "audit_diff":
            pr = payload.get("pr_number")
            if pr:
                return f"Auditing only the changed lines in pull request {pr}."
            return "Auditing only the changed lines in that diff."
        if tool == "evaluate_sla":
            return "Checking that deployment against your energy SLA."
        if tool == "scope_inventory":
            return "Building your Scope 1, 2 and 3 emissions inventory."
        if tool == "audit_history":
            return "Pulling up your recent audit history and carbon savings."
        if tool == "dynamic_analyze":
            return (
                "Running that repository in a sandbox to measure what it "
                "actually costs."
            )
        if tool == "help":
            return "Here is what I can do for you."
        return "Running your GreenCode command."

    @staticmethod
    def _fallback(utterance: str, hint: Optional[str] = None) -> AlexaCommand:
        if hint is None:
            hint = (
                "I did not catch that. Try: 'audit my repository', "
                "'what is my green score', 'compare Ireland and Virginia', "
                "'measure energy', or 'refactor my code'."
            )
        return AlexaCommand(
            tool="help",
            payload={"hint": hint},
            summary=hint,
            confidence=0.0,
            raw_utterance=utterance,
            fallback=True,
        )


MAPPER = AlexaNLUMapper()


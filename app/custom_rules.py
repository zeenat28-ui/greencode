"""Declarative YAML/JSON Custom Energy Rule Engine for GreenCode Auditor.

Allows engineering teams to author and enforce organization-specific static
carbon and FinOps rules via `.greencode-rules.yaml` or HTTP API payloads.
"""

import ast
from functools import lru_cache
import json
import os
import re
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

DEFAULT_CUSTOM_RULES: List[Dict[str, Any]] = [
    {
        "id": "CUSTOM_SLEEP_POLLING_IN_LOOP",
        "title": "Busy-Wait time.sleep() Polling Inside Loop",
        "description": (
            "Polling with time.sleep() inside a loop holds worker threads and prevents "
            "CPU package C-state residency. Prefer event-driven callbacks or asyncio.Event."
        ),
        "ast_call_in_loop": "time.sleep",
        "pattern_regex": r"(?:for|while)[ \t]+[^\n:]+:[ \t]*(?:\n[ \t]+[^\s\n][^\n]*){0,6}\n[ \t]+time\.sleep\s*\(",
        "languages": ["python"],
        "severity": "MEDIUM",
        "deduction": 6.0,
        "gsf_pattern": "GSF-custom-01: Event-Driven Scheduling Over Polling",
        "fix_guidance": "Replace busy-wait sleep loops with asyncio.Event.wait(), queue blocking reads, or webhook triggers.",
    },
    {
        "id": "CUSTOM_PANDAS_CSV_NO_CHUNKSIZE",
        "title": "Unbounded pandas.read_csv() Inside Iteration",
        "description": (
            "Loading full CSV frames repeatedly inside a loop spikes DRAM allocation "
            "and memory controller power draw."
        ),
        "ast_call_in_loop": "pd.read_csv",
        "pattern_regex": r"(?:for|while)[ \t]+[^\n:]+:[ \t]*(?:\n[ \t]+[^\s\n][^\n]*){0,6}\n[ \t]+[^\s\n][^\n]*\bpd\.read_csv\s*\(",
        "languages": ["python"],
        "severity": "HIGH",
        "deduction": 10.0,
        "gsf_pattern": "GSF-custom-02: Streaming Data Ingestion",
        "fix_guidance": "Hoist pd.read_csv() outside the loop or stream large datasets with chunksize=10000 and usecols=[...].",
    },
    {
        "id": "CUSTOM_CONSOLE_LOG_IN_HOT_LOOP",
        "title": "Synchronous Console/Stdout Serialization in Loop",
        "description": (
            "Calling console.log() inside a tight loop forces synchronous string formatting "
            "and I/O buffer flushes on every iteration."
        ),
        "pattern_regex": r"for\s*\([^)]+\)\s*\{[^}]{0,400}\bconsole\.log\s*\(",
        "languages": ["javascript", "typescript"],
        "severity": "LOW",
        "deduction": 3.5,
        "gsf_pattern": "GSF-custom-03: Batched Structured Logging",
        "fix_guidance": "Aggregate diagnostics in memory or sample logs outside the hot loop.",
    },
    {
        "id": "CUSTOM_JSON_DUMPS_IN_LOOP",
        "title": "Repeated JSON Full-Object Serialization in Loop",
        "description": (
            "Serializing full dictionaries with json.dumps() on every iteration wastes CPU "
            "cycles on redundant string encoding."
        ),
        "ast_call_in_loop": "json.dumps",
        "pattern_regex": r"(?:for|while)[ \t]+[^\n:]+:[ \t]*(?:\n[ \t]+[^\s\n][^\n]*){0,6}\n[ \t]+[^\s\n][^\n]*\bjson\.dumps\s*\(",
        "languages": ["python"],
        "severity": "MEDIUM",
        "deduction": 5.5,
        "gsf_pattern": "GSF-custom-04: Hoisted Payload Serialization",
        "fix_guidance": "Pre-serialize invariant payloads outside the loop or stream newline-delimited JSON.",
    },
]


@lru_cache(maxsize=256)
def _compile_cached_regex(pattern_str: str) -> Optional[re.Pattern]:
    """Compile and cache a regular expression outside iteration loops."""
    try:
        return re.compile(pattern_str, re.MULTILINE)
    except re.error:
        return None


def parse_custom_rules_yaml(raw_text: str) -> List[Dict[str, Any]]:
    """Parse a `.greencode-rules.yaml` or JSON string into normalized rule dictionaries."""
    cleaned = (raw_text or "").strip()
    if not cleaned:
        return list(DEFAULT_CUSTOM_RULES)

    parsed: Any = None
    if cleaned.startswith("{") or cleaned.startswith("["):
        try:
            parsed = json.loads(cleaned)
        except Exception:
            parsed = None

    if parsed is None and YAML_AVAILABLE:
        try:
            parsed = yaml.safe_load(cleaned)
        except Exception:
            parsed = None

    if isinstance(parsed, dict) and isinstance(parsed.get("rules"), list):
        return _normalize_rule_list(parsed["rules"])
    if isinstance(parsed, list):
        return _normalize_rule_list(parsed)
    return list(DEFAULT_CUSTOM_RULES)


def _normalize_single_rule(item: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    rule_id = str(item.get("id") or "").strip()
    pattern_regex = str(item.get("pattern_regex") or item.get("pattern") or "").strip()
    ast_call_in_loop = str(item.get("ast_call_in_loop") or "").strip()
    if not rule_id or (not pattern_regex and not ast_call_in_loop):
        return None
    langs = item.get("languages") or ["python"]
    if isinstance(langs, str):
        langs = [langs]
    return {
        "id": rule_id,
        "title": str(item.get("title") or rule_id),
        "description": str(item.get("description") or "Custom declarative energy rule match."),
        "ast_call_in_loop": ast_call_in_loop,
        "pattern_regex": pattern_regex,
        "languages": [str(x).lower() for x in langs],
        "severity": str(item.get("severity") or "MEDIUM").upper(),
        "deduction": float(item.get("deduction") or 5.0),
        "gsf_pattern": str(item.get("gsf_pattern") or "GSF-custom: Organization Energy Policy"),
        "fix_guidance": str(item.get("fix_guidance") or "Refactor the matched pattern per organizational energy policy."),
    }


def _normalize_rule_list(raw_rules: List[Any]) -> List[Dict[str, Any]]:
    normalized = [_normalize_single_rule(r) for r in raw_rules]
    return [r for r in normalized if r is not None]


def load_repo_custom_rules(repo_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load `.greencode-rules.yaml` from the given directory or repository root."""
    candidates = []
    if repo_root:
        candidates.append(os.path.join(repo_root, ".greencode-rules.yaml"))
        candidates.append(os.path.join(repo_root, ".greencode-rules.yml"))
    default_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    candidates.append(os.path.join(default_root, ".greencode-rules.yaml"))

    resolved_path = next((p for p in candidates if os.path.isfile(p)), None)
    if resolved_path:
        try:
            with open(resolved_path, "r", encoding="utf-8", errors="replace") as f:
                return parse_custom_rules_yaml(f.read())
        except Exception:
            pass
    return list(DEFAULT_CUSTOM_RULES)


def _extract_dotted_call(call_node: ast.Call) -> str:
    func = call_node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts: List[str] = [func.attr]
        curr = func.value
        while isinstance(curr, ast.Attribute):
            parts.append(curr.attr)
            curr = curr.value
        if isinstance(curr, ast.Name):
            parts.append(curr.id)
        parts.reverse()
        return ".".join(parts)
    return ""


def _collect_ast_loop_calls(tree: ast.AST) -> List[tuple]:
    """Return list of (loop_line, call_line, dotted_call_name) for all calls inside AST loops."""
    collected: List[tuple] = []
    loop_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp))
    ]
    for loop_node in loop_nodes:
        loop_line = int(getattr(loop_node, "lineno", 1))
        for child in ast.walk(loop_node):
            if isinstance(child, ast.Call):
                cname = _extract_dotted_call(child)
                if cname:
                    collected.append((loop_line, int(getattr(child, "lineno", loop_line)), cname))
    return collected


def _match_ast_selector(
    rule: Dict[str, Any],
    ast_loop_calls: List[tuple],
    lines: List[str],
    language: str,
    file_path: str,
) -> List[Dict[str, Any]]:
    """Match a structural `ast_call_in_loop` rule against pre-extracted AST loop calls."""
    target_call = str(rule.get("ast_call_in_loop") or "").strip()
    if not target_call:
        return []
    findings: List[Dict[str, Any]] = []
    seen_lines = set()
    for loop_line, call_line, cname in ast_loop_calls:
        if cname != target_call and not cname.endswith("." + target_call.split(".")[-1]) or (
            "." in target_call and cname != target_call
        ):
            continue
        if call_line in seen_lines:
            continue
        seen_lines.add(call_line)
        snippet_lines = lines[max(0, loop_line - 1): min(len(lines), call_line)]
        snippet_text = "\n".join(snippet_lines).strip()
        if "greencode: ignore" in snippet_text or "greencode:ignore" in snippet_text:
            continue
        findings.append({
            "violation_type": rule["id"],
            "severity": rule["severity"],
            "title": rule["title"],
            "description": rule["description"],
            "line_number": loop_line,
            "end_line_number": max(loop_line, call_line),
            "deduction": float(rule["deduction"]),
            "gsf_pattern": rule["gsf_pattern"],
            "suggested_fix": rule["fix_guidance"],
            "file_path": file_path,
            "language": language,
            "snippet": snippet_text[:300],
            "complexity_class": "O(N_custom_ast_rule)",
            "span_lines": max(1, call_line - loop_line + 1),
            "custom_rule": True,
        })
    return findings


def _match_single_rule(
    rule: Dict[str, Any],
    source_code: str,
    lines: List[str],
    language: str,
    file_path: str,
    ast_loop_calls: Optional[List[tuple]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate a single pre-normalized custom rule against source_code."""
    allowed_langs = rule.get("languages", [])
    if allowed_langs and "*" not in allowed_langs and language.lower() not in allowed_langs:
        return []

    if language.lower() == "python" and rule.get("ast_call_in_loop") and ast_loop_calls is not None:
        ast_matches = _match_ast_selector(rule, ast_loop_calls, lines, language, file_path)
        if ast_matches:
            return ast_matches

    pattern_regex = rule.get("pattern_regex") or ""
    if not pattern_regex:
        return []
    compiled = _compile_cached_regex(pattern_regex)
    if compiled is None:
        return []

    findings: List[Dict[str, Any]] = []
    for match in compiled.finditer(source_code):
        start_idx = match.start()
        end_idx = match.end()
        line_num = source_code.count("\n", 0, start_idx) + 1
        end_line = source_code.count("\n", 0, end_idx) + 1
        snippet_lines = lines[max(0, line_num - 1): min(len(lines), end_line)]
        snippet_text = "\n".join(snippet_lines).strip()
        if "greencode: ignore" in snippet_text or "greencode:ignore" in snippet_text:
            continue
        findings.append({
            "violation_type": rule["id"],
            "severity": rule["severity"],
            "title": rule["title"],
            "description": rule["description"],
            "line_number": line_num,
            "end_line_number": max(line_num, end_line),
            "deduction": float(rule["deduction"]),
            "gsf_pattern": rule["gsf_pattern"],
            "suggested_fix": rule["fix_guidance"],
            "file_path": file_path,
            "language": language,
            "snippet": snippet_text[:300],
            "complexity_class": "O(N_custom_rule)",
            "span_lines": max(1, end_line - line_num + 1),
            "custom_rule": True,
        })
    return findings


def evaluate_custom_rules(
    source_code: str,
    language: str = "python",
    file_path: str = "code.py",
    custom_rules: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate active custom rules against source_code and return violation records."""
    if not source_code:
        return []

    rules = custom_rules if custom_rules is not None else load_repo_custom_rules()
    lines = source_code.splitlines()
    ast_loop_calls: Optional[List[tuple]] = None
    if language.lower() == "python":
        try:
            tree = ast.parse(source_code)
            ast_loop_calls = _collect_ast_loop_calls(tree)
        except SyntaxError:
            ast_loop_calls = None

    all_findings: List[Dict[str, Any]] = []
    for rule in rules:
        all_findings.extend(
            _match_single_rule(rule, source_code, lines, language, file_path, ast_loop_calls)
        )
    return all_findings

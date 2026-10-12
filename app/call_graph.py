"""Cross-File Inter-Procedural Call Graph & Symbol Analyzer for GreenCode.

Resolves function and method calls across repository files (Python, TypeScript,
JavaScript, Go, and Rust) to detect hidden N+1 database queries, uncached HTTP
requests, and nested loop complexity when a loop in File A invokes a helper
function defined in File B (or transitively in File C).
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

_NETWORK_CALLEES: Set[str] = {
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.delete",
    "requests.request",
    "httpx.get",
    "httpx.post",
    "urllib.request.urlopen",
    "urlopen",
    "aiohttp.ClientSession.get",
    "fetch",
    "axios.get",
    "axios.post",
    "axios.request",
    "http.Get",
    "http.Post",
    "client.Do",
    "reqwest.get",
    "reqwest::get",
    "client.get",
    "client.post",
}

_DATABASE_CALLEES: Set[str] = {
    "cursor.execute",
    "cursor.executemany",
    "session.execute",
    "session.query",
    "session.scalars",
    "conn.execute",
    "connection.execute",
    "db.execute",
    "db.query",
    "engine.execute",
    "pool.query",
    "client.query",
    "prisma.user.findUnique",
    "prisma.user.findMany",
    "db.Query",
    "db.QueryRow",
    "db.Exec",
    "sqlx.query",
    "sqlx::query",
}

_FILESYSTEM_CALLEES: Set[str] = {
    "pd.read_csv",
    "pandas.read_csv",
    "pd.read_parquet",
    "Path.read_text",
    "Path.read_bytes",
    "fs.readFileSync",
    "fs.readFile",
    "os.ReadFile",
    "ioutil.ReadFile",
    "fs.read_to_string",
    "std::fs::read_to_string",
    "fs::read_to_string",
}

_EXT_TO_LANG: Dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
}

# Precompiled function header patterns for brace-scoped languages (TS/JS, Go, Rust)
_RE_BRACE_FUNC_HEADER = re.compile(
    r"(?:^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+([A-Za-z_]\w*)\s*\([^)]*\)[^{]*\{)"
    r"|(?:^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_]\w*)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]+)?=>\s*\{)"
    r"|(?:^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_]\w*)\s*\([^)]*\)[^{]*\{)"
    r"|(?:^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\([^)]*\)[^{]*\{)",
    re.MULTILINE,
)

_RE_BRACE_LOOP_HEADER = re.compile(
    r"(?:\b(?:for|while|loop)\b[^{;]*\{)|(?:\.\s*forEach\s*\([^{]*\{)",
    re.MULTILINE,
)

_RE_BRACE_CALL = re.compile(
    r"\b([A-Za-z_]\w*(?:(?:\.|::)[A-Za-z_]\w*)*)\s*\("
)

_CONTROL_KEYWORDS: Set[str] = {
    "if", "for", "while", "switch", "catch", "return", "sizeof", "match",
    "loop", "function", "func", "fn", "Some", "Ok", "Err", "vec", "println",
    "fmt.Sprintf", "len", "make", "append", "new",
}


def _detect_file_language(file_path: str) -> Optional[str]:
    """Map a file extension to a supported call-graph language."""
    lower = file_path.lower()
    for ext, lang in _EXT_TO_LANG.items():
        if lower.endswith(ext):
            return lang
    return None


@dataclass
class FunctionSymbol:
    """Represents a function or method node in the repository call graph."""

    name: str
    qualified_name: str
    file_path: str
    line_number: int
    language: str = "python"
    direct_sink_kind: Optional[str] = None
    direct_sink_callee: Optional[str] = None
    has_internal_loop: bool = False
    called_symbols: List[str] = field(default_factory=list)
    transitive_sink_kind: Optional[str] = None
    sink_chain: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "language": self.language,
            "direct_sink_kind": self.direct_sink_kind,
            "direct_sink_callee": self.direct_sink_callee,
            "has_internal_loop": self.has_internal_loop,
            "called_symbols": list(self.called_symbols),
            "transitive_sink_kind": self.transitive_sink_kind,
            "sink_chain": list(self.sink_chain),
        }


def _extract_call_name(call_node: ast.Call) -> str:
    """Return dotted call name such as 'requests.get' or simple name 'fetch_user'."""
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


def _classify_direct_call(call_name: str) -> Optional[str]:
    """Classify a dotted/scoped call name as network, database, or filesystem I/O."""
    if not call_name:
        return None
    norm = call_name.replace("::", ".")
    if call_name in _NETWORK_CALLEES or norm in _NETWORK_CALLEES:
        return "network"
    if norm.endswith((".get", ".post", ".Get", ".Post", ".Do", ".send")) and norm.startswith(
        ("requests.", "httpx.", "client.", "http.", "axios.", "reqwest.")
    ):
        return "network"
    if call_name in _DATABASE_CALLEES or norm in _DATABASE_CALLEES:
        return "database"
    if norm.endswith(
        (".execute", ".query", ".scalars", ".fetchone", ".fetchall", ".Query", ".QueryRow", ".Exec", ".findUnique", ".findMany")
    ):
        return "database"
    if call_name in _FILESYSTEM_CALLEES or norm in _FILESYSTEM_CALLEES or norm.endswith(
        (".readFileSync", ".readFile", ".ReadFile", ".read_to_string")
    ):
        return "filesystem"
    return None


def _analyze_function_body(
    fn_node: ast.AST, file_path: str, class_prefix: str = ""
) -> FunctionSymbol:
    """Inspect a single Python function/method AST node for direct sinks and outgoing calls."""
    fn_name = getattr(fn_node, "name", "anonymous")
    qual_name = f"{class_prefix}.{fn_name}" if class_prefix else fn_name
    line_no = int(getattr(fn_node, "lineno", 1))

    direct_kind: Optional[str] = None
    direct_callee: Optional[str] = None
    has_loop = False
    outgoing: List[str] = []

    for child in ast.walk(fn_node):
        if child is not fn_node and isinstance(child, (ast.For, ast.AsyncFor, ast.While)):
            has_loop = True
        elif isinstance(child, ast.Call):
            cname = _extract_call_name(child)
            if not cname:
                continue
            io_kind = _classify_direct_call(cname)
            if io_kind and direct_kind is None:
                direct_kind = io_kind
                direct_callee = cname
            short_name = cname.split(".")[-1]
            if short_name not in outgoing:
                outgoing.append(short_name)

    if direct_kind is None and has_loop:
        direct_kind = "loop_compute"
        direct_callee = "internal_iteration"

    chain_start = [f"{file_path}:{qual_name}"]
    if direct_callee:
        chain_start.append(direct_callee)

    return FunctionSymbol(
        name=fn_name,
        qualified_name=qual_name,
        file_path=file_path,
        line_number=line_no,
        language="python",
        direct_sink_kind=direct_kind,
        direct_sink_callee=direct_callee,
        has_internal_loop=has_loop,
        called_symbols=outgoing,
        transitive_sink_kind=direct_kind,
        sink_chain=chain_start if direct_kind else [],
    )


def _find_matching_brace(source: str, open_brace_idx: int) -> int:
    """Return index of the matching closing '}' for the '{' at open_brace_idx."""
    depth = 0
    idx = open_brace_idx
    length = len(source)
    while idx < length:
        ch = source[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return idx
        idx += 1
    return length - 1


def _extract_brace_function_symbol(
    match: re.Match, source_code: str, file_path: str, language: str
) -> FunctionSymbol:
    """Build a FunctionSymbol from a brace-scoped function header match."""
    fn_name = next((g for g in match.groups() if g), "anonymous")
    line_no = source_code.count("\n", 0, match.start()) + 1
    open_idx = match.end() - 1
    close_idx = _find_matching_brace(source_code, open_idx)
    body = source_code[open_idx + 1 : close_idx]

    has_loop = bool(_RE_BRACE_LOOP_HEADER.search(body))
    direct_kind: Optional[str] = None
    direct_callee: Optional[str] = None
    outgoing: List[str] = []

    for call_match in _RE_BRACE_CALL.finditer(body):
        raw_callee = call_match.group(1)
        if raw_callee in _CONTROL_KEYWORDS:
            continue
        io_kind = _classify_direct_call(raw_callee)
        if io_kind and direct_kind is None:
            direct_kind = io_kind
            direct_callee = raw_callee
        short_name = raw_callee.replace("::", ".").rsplit(".", 1)[-1]
        if short_name not in outgoing and short_name != fn_name:
            outgoing.append(short_name)

    if direct_kind is None and has_loop:
        direct_kind = "loop_compute"
        direct_callee = "internal_iteration"

    chain_start = [f"{file_path}:{fn_name}"]
    if direct_callee:
        chain_start.append(direct_callee)

    return FunctionSymbol(
        name=fn_name,
        qualified_name=fn_name,
        file_path=file_path,
        line_number=line_no,
        language=language,
        direct_sink_kind=direct_kind,
        direct_sink_callee=direct_callee,
        has_internal_loop=has_loop,
        called_symbols=outgoing,
        transitive_sink_kind=direct_kind,
        sink_chain=chain_start if direct_kind else [],
    )


def _extract_brace_language_symbols(
    file_path: str, source_code: str, language: str
) -> List[FunctionSymbol]:
    """Extract function symbols from TypeScript, JavaScript, Go, or Rust source code."""
    return [
        _extract_brace_function_symbol(m, source_code, file_path, language)
        for m in _RE_BRACE_FUNC_HEADER.finditer(source_code)
    ]


def _extract_file_symbols(file_path: str, source_code: str) -> List[FunctionSymbol]:
    """Parse a source file and return all function/method symbols across supported languages."""
    lang = _detect_file_language(file_path)
    if lang is None:
        return []
    if lang != "python":
        return _extract_brace_language_symbols(file_path, source_code, lang)

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    symbols: List[FunctionSymbol] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(_analyze_function_body(node, file_path))
        elif isinstance(node, ast.ClassDef):
            symbols.extend(_extract_class_methods(node, file_path))
    return symbols


def _extract_class_methods(class_node: ast.ClassDef, file_path: str) -> List[FunctionSymbol]:
    """Extract method symbols from a class definition."""
    methods: List[FunctionSymbol] = []
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_analyze_function_body(item, file_path, class_prefix=class_node.name))
    return methods


def _propagate_single_pass(symbol_map: Dict[str, FunctionSymbol]) -> bool:
    """Run one propagation pass across the call graph; return True if any symbol updated."""
    changed = False
    for sym in symbol_map.values():
        if sym.transitive_sink_kind in ("network", "database", "filesystem"):
            continue
        best_target = _find_called_sink(sym, symbol_map)
        if best_target is not None:
            sym.transitive_sink_kind = best_target.transitive_sink_kind
            sym.sink_chain = [f"{sym.file_path}:{sym.qualified_name}"] + list(best_target.sink_chain)
            changed = True
    return changed


def _find_called_sink(
    caller: FunctionSymbol, symbol_map: Dict[str, FunctionSymbol]
) -> Optional[FunctionSymbol]:
    """Return the first called symbol that has a transitive sink."""
    for callee_name in caller.called_symbols:
        target = symbol_map.get(callee_name)
        if target is not None and target is not caller and target.transitive_sink_kind:
            return target
    return None


def build_repository_call_graph(files: Dict[str, str]) -> Dict[str, FunctionSymbol]:
    """Build an inter-procedural symbol table across multiple repository files."""
    symbol_map: Dict[str, FunctionSymbol] = {}
    for file_path, source_code in files.items():
        if _detect_file_language(file_path) is None:
            continue
        for sym in _extract_file_symbols(file_path, source_code):
            symbol_map[sym.name] = sym
            symbol_map[sym.qualified_name] = sym

    for _ in range(6):
        if not _propagate_single_pass(symbol_map):
            break

    return symbol_map


def _build_violation_record(
    file_path: str,
    language: str,
    line_no: int,
    target: FunctionSymbol,
    source_lines: List[str],
) -> Dict[str, Any]:
    """Construct a structured cross-file violation dictionary for any supported language."""
    sink_kind = target.transitive_sink_kind or "io"
    snippet = source_lines[line_no - 1].strip() if 1 <= line_no <= len(source_lines) else ""
    chain_str = " -> ".join(target.sink_chain)

    if sink_kind == "network":
        v_type = "CROSS_FILE_NETWORK_IN_LOOP"
        title = f"Cross-File Network I/O Inside Loop via '{target.name}()'"
        severity = "CRITICAL"
        deduction = 18.0
        fix = (
            f"Hoist '{target.name}()' outside the loop or batch payloads across files "
            f"(call chain: {chain_str})."
        )
    elif sink_kind in ("database", "filesystem"):
        v_type = "CROSS_FILE_DB_IN_LOOP"
        title = f"Cross-File N+1 Query / Storage Read Inside Loop via '{target.name}()'"
        severity = "HIGH"
        deduction = 15.0
        fix = (
            f"Replace per-item '{target.name}()' calls with a bulk IN query or preloaded map "
            f"(call chain: {chain_str})."
        )
    else:
        v_type = "CROSS_FILE_COMPUTE_IN_LOOP"
        title = f"Cross-File Nested Loop Complexity via '{target.name}()'"
        severity = "MEDIUM"
        deduction = 10.0
        fix = (
            f"Pre-index or vectorize '{target.name}()' defined in '{target.file_path}' "
            f"to avoid compounding O(N^2) iteration (call chain: {chain_str})."
        )

    return {
        "file_path": file_path,
        "language": language,
        "line_number": line_no,
        "end_line_number": line_no,
        "violation_type": v_type,
        "title": title,
        "severity": severity,
        "deduction": deduction,
        "gsf_pattern": "GSF-interproc-01: Cross-Module I/O & Loop Hoisting",
        "description": (
            f"Loop in '{file_path}' (line {line_no}) invokes '{target.qualified_name}' "
            f"defined in '{target.file_path}' (line {target.line_number}), triggering "
            f"transitive '{sink_kind}' execution on every iteration ({chain_str})."
        ),
        "suggested_fix": fix,
        "call_chain": list(target.sink_chain),
        "callee_file": target.file_path,
        "callee_line": target.line_number,
        "snippet": snippet,
    }


def _inspect_brace_loop_span(
    loop_match: re.Match,
    file_path: str,
    language: str,
    source_code: str,
    source_lines: List[str],
    symbol_map: Dict[str, FunctionSymbol],
    seen_sites: Set[Tuple[int, str]],
) -> List[Dict[str, Any]]:
    """Inspect a single brace-delimited loop block in TS/JS, Go, or Rust for cross-file calls."""
    open_idx = loop_match.end() - 1
    close_idx = _find_matching_brace(source_code, open_idx)
    loop_body = source_code[open_idx + 1 : close_idx]
    body_start_offset = open_idx + 1
    found: List[Dict[str, Any]] = []

    for call_match in _RE_BRACE_CALL.finditer(loop_body):
        raw_callee = call_match.group(1)
        if raw_callee in _CONTROL_KEYWORDS:
            continue
        short_name = raw_callee.replace("::", ".").rsplit(".", 1)[-1]
        target = symbol_map.get(raw_callee) or symbol_map.get(short_name)
        if target is None or not target.transitive_sink_kind:
            continue
        abs_offset = body_start_offset + call_match.start()
        line_no = source_code.count("\n", 0, abs_offset) + 1
        site_key = (line_no, target.qualified_name)
        if site_key in seen_sites:
            continue
        seen_sites.add(site_key)
        found.append(_build_violation_record(file_path, language, line_no, target, source_lines))
    return found


def _scan_brace_language_loop_calls(
    file_path: str,
    language: str,
    source_code: str,
    symbol_map: Dict[str, FunctionSymbol],
) -> List[Dict[str, Any]]:
    """Scan all loop blocks in a TypeScript, JavaScript, Go, or Rust file for cross-file calls."""
    source_lines = source_code.splitlines()
    seen_sites: Set[Tuple[int, str]] = set()
    violations: List[Dict[str, Any]] = []
    for loop_match in _RE_BRACE_LOOP_HEADER.finditer(source_code):
        violations.extend(
            _inspect_brace_loop_span(
                loop_match, file_path, language, source_code, source_lines, symbol_map, seen_sites
            )
        )
    return violations


def _scan_loop_calls_in_file(
    file_path: str,
    source_code: str,
    symbol_map: Dict[str, FunctionSymbol],
) -> List[Dict[str, Any]]:
    """Scan all loop nodes in a file for calls into expensive call-graph symbols."""
    lang = _detect_file_language(file_path)
    if lang is None:
        return []
    if lang != "python":
        return _scan_brace_language_loop_calls(file_path, lang, source_code, symbol_map)

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    source_lines = source_code.splitlines()
    violations: List[Dict[str, Any]] = []
    seen_sites: Set[Tuple[int, str]] = set()

    loop_nodes = [
        n for n in ast.walk(tree)
        if isinstance(n, (ast.For, ast.AsyncFor, ast.While, ast.ListComp, ast.SetComp))
    ]
    for loop_node in loop_nodes:
        violations.extend(
            _inspect_single_loop_node(loop_node, file_path, source_lines, symbol_map, seen_sites)
        )
    return violations


def _inspect_single_loop_node(
    loop_node: ast.AST,
    file_path: str,
    source_lines: List[str],
    symbol_map: Dict[str, FunctionSymbol],
    seen_sites: Set[Tuple[int, str]],
) -> List[Dict[str, Any]]:
    """Check all function calls inside a single Python loop AST node against the symbol map."""
    found: List[Dict[str, Any]] = []
    for child in ast.walk(loop_node):
        if not isinstance(child, ast.Call):
            continue
        cname = _extract_call_name(child)
        short_name = cname.split(".")[-1] if cname else ""
        target = symbol_map.get(cname) or symbol_map.get(short_name)
        if target is None or not target.transitive_sink_kind:
            continue
        line_no = int(getattr(child, "lineno", 1))
        site_key = (line_no, target.qualified_name)
        if site_key in seen_sites:
            continue
        seen_sites.add(site_key)
        found.append(_build_violation_record(file_path, "python", line_no, target, source_lines))
    return found


def audit_cross_file_loops(files: Dict[str, str]) -> Dict[str, Any]:
    """Perform cross-file call-graph analysis across a mapping of `{file_path: source_code}`."""
    symbol_map = build_repository_call_graph(files)
    all_violations: List[Dict[str, Any]] = []

    for file_path, source_code in files.items():
        if _detect_file_language(file_path) is None:
            continue
        all_violations.extend(_scan_loop_calls_in_file(file_path, source_code, symbol_map))

    total_deduction = sum(float(v.get("deduction", 10.0)) for v in all_violations)
    green_score = round(max(0.0, 100.0 - total_deduction), 2)
    grade = "A" if green_score >= 90 else "B" if green_score >= 80 else "C" if green_score >= 70 else "D" if green_score >= 60 else "F"

    unique_symbols = {
        f"{s.file_path}:{s.qualified_name}": s.to_dict()
        for s in symbol_map.values()
    }

    return {
        "files_scanned": len(files),
        "symbols_indexed": len(unique_symbols),
        "total_violations": len(all_violations),
        "green_score": green_score,
        "grade": grade,
        "violations": all_violations,
        "call_graph": list(unique_symbols.values()),
    }

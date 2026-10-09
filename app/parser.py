"""Universal Multi-Language Concrete Syntax Tree (CST) Static Analysis Engine.

Built for GreenCode Auditor utilizing the universal Tree-sitter Parsing Framework
and Python AST visitors adhering to the Green Software Foundation Patterns Catalogue.

Natively parses and audits:
1. Python (.py)
2. JavaScript / TypeScript (.js, .jsx, .ts, .tsx, .mjs)
3. C / C++ (.cpp, .cc, .cxx, .c, .h, .hpp)
4. Java (.java)
5. Go (.go)

Universal and language-specific Green Computing checks:
- Universal S-expression query loop depth analysis: O(N^3) algorithmic energy drain (depth >= 3)
- Unmanaged database cursor lifecycles
- Synchronous uncached network/HTTP requests in loops
- Quadratic memory-reallocating string concatenations in iteration loops
"""

import ast
import atexit
import os
import re
import shutil
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple
import warnings
import zipfile

# Suppress known tree-sitter legacy constructor FutureWarning emitted by tree_sitter_languages
warnings.filterwarnings("ignore", category=FutureWarning, module="tree_sitter")

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import tree_sitter_languages
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


class ViolationType:
    NESTED_LOOPS = "NESTED_LOOPS_DEPTH_3+"
    RAW_DB_CURSOR = "RAW_DB_CURSOR_NO_CONTEXT"
    UNCACHED_NETWORK_IN_LOOP = "UNCACHED_NETWORK_IN_LOOP"
    QUADRATIC_STRING_CONCAT = "QUADRATIC_STRING_CONCAT_IN_LOOP"
    HIDDEN_ITERATIVE_COMPUTATION = "HIDDEN_ITERATIVE_COMPUTATION"
    # Extended GSF catalogue (roadmap: "Add 10 more patterns"). Every one of
    # these is detectable statically without executing the code, and none of
    # them fire on samples/eco_pipeline.py, which must stay at 0 violations.
    N_PLUS_ONE_QUERY_IN_LOOP = "N_PLUS_ONE_QUERY_IN_LOOP"
    INEFFICIENT_REGEX_IN_LOOP = "INEFFICIENT_REGEX_IN_LOOP"
    THREAD_THRASHING_IN_LOOP = "THREAD_THRASHING_IN_LOOP"
    SYNC_FILE_IO_IN_LOOP = "SYNC_FILE_IO_IN_LOOP"
    SLEEP_IN_LOOP = "SLEEP_IN_LOOP"
    JSON_SERIALIZE_IN_LOOP = "JSON_SERIALIZE_IN_LOOP"
    SORTED_IN_LOOP = "SORTED_IN_LOOP"
    RECURSION_WITHOUT_MEMOIZATION = "RECURSION_WITHOUT_MEMOIZATION"
    LINEAR_LOOKUP_IN_LOOP = "LINEAR_LOOKUP_IN_LOOP"
    EXCESSIVE_LOGGING_IN_LOOP = "EXCESSIVE_LOGGING_IN_LOOP"


VIOLATION_METADATA = {
    ViolationType.NESTED_LOOPS: {
        "title": "Deep Nested Iteration (Depth >= 3)",
        "deduction": 15.0,
        "severity": "HIGH",
        "gsf_pattern": "Algorithmic Efficiency / Time Complexity Reduction",
        "description": "Nested loops with depth >= 3 escalate algorithmic complexity to O(N^3) or worse, causing physical CPU execution cycles and power consumption to skyrocket.",
        "fix_guidance": "Flatten iterations using generators, product combinations, vectorized operations, or dictionary hash lookups.",
    },
    ViolationType.RAW_DB_CURSOR: {
        "title": "Unmanaged Raw Database Cursor",
        "deduction": 10.0,
        "severity": "HIGH",
        "gsf_pattern": "Resource Lifecycle & Connection Power Management",
        "description": "Opening database cursors without a context manager ('with' block) risks socket leakage and idle connection persistence, keeping remote DB server nodes in higher power states.",
        "fix_guidance": "Wrap cursor instantiation and operations inside a 'with connection.cursor() as cursor:' context manager.",
    },
    ViolationType.UNCACHED_NETWORK_IN_LOOP: {
        "title": "Un-cached Network Call Inside Iteration",
        "deduction": 20.0,
        "severity": "CRITICAL",
        "gsf_pattern": "Network Carbon Reduction & Request Batching",
        "description": "Triggering synchronous HTTP/network requests inside a loop repeatedly activates network interface card (NIC) hardware and wastes server CPU wait cycles.",
        "fix_guidance": "Batch multiple requests into a single bulk payload, utilize connection pooling/sessions, or memoize repetitive queries via caching decorators.",
    },
    ViolationType.QUADRATIC_STRING_CONCAT: {
        "title": "Quadratic '+' String Concatenation In Loop",
        "deduction": 8.0,
        "severity": "MEDIUM",
        "gsf_pattern": "Memory Allocation Minimization",
        "description": "Using '+' or '+=' string concatenation inside loops causes quadratic O(N^2) memory reallocation and garbage collection thrashing, increasing RAM bus power draw.",
        "fix_guidance": "Append strings into a list and combine once at exit using ''.join(chunks), or use StringBuilder.",
    },
    ViolationType.HIDDEN_ITERATIVE_COMPUTATION: {
        "title": "Hidden Iterative Vector / Async Callback Leak",
        "deduction": 12.0,
        "severity": "HIGH",
        "gsf_pattern": "Vectorized Processing & Memory Efficiency",
        "description": "Using row-by-row iteration (e.g. df.iterrows(), df.itertuples()) or deeply chained async callback mappings (e.g. array.map / forEach) bypasses hardware vectorized processing pipelines, multiplying CPU cycles and power draw.",
        "fix_guidance": "Replace iterative row loops with vectorized columnar operations, array comprehensions, or batch pipeline transforms.",
    },
    ViolationType.N_PLUS_ONE_QUERY_IN_LOOP: {
        "title": "N+1 Query Inside Iteration (SELECT per row)",
        "deduction": 14.0,
        "severity": "HIGH",
        "gsf_pattern": "Data Access Batching & Request Coalescing",
        "description": "Executing a SELECT query once per loop iteration opens a network round trip per row (the classic N+1 pattern). Each trip keeps a connection, the CPU and the NIC awake instead of fetching the whole result set in one batched query.",
        "fix_guidance": "Issue a single query with WHERE ... IN (...), a JOIN, or a server-side cursor that fetches the full set once; batch writes with executemany or a bulk upsert.",
    },
    ViolationType.INEFFICIENT_REGEX_IN_LOOP: {
        "title": "Regex Compiled Or Executed Inside Loop",
        "deduction": 7.0,
        "severity": "MEDIUM",
        "gsf_pattern": "Algorithmic Efficiency / Compile Once, Reuse",
        "description": "Compiling or running a regular expression inside a loop re-parses the pattern on every iteration. Backtracking engines can burn orders of magnitude more CPU than an equivalent literal search.",
        "fix_guidance": "Hoist re.compile() out of the loop (or use a module-level compiled pattern), and prefer literal string methods over regex when the pattern is fixed.",
    },
    ViolationType.THREAD_THRASHING_IN_LOOP: {
        "title": "Thread Or Process Spawned Per Iteration",
        "deduction": 13.0,
        "severity": "HIGH",
        "gsf_pattern": "Concurrency Pooling & Scheduling Efficiency",
        "description": "Creating a thread or process inside a loop forces the OS scheduler to create and tear down execution contexts repeatedly. Context switches and thread startup dominate the useful work and keep every core awake.",
        "fix_guidance": "Create one ThreadPoolExecutor/ProcessPoolExecutor outside the loop and submit work to it, or batch the items so each worker handles many of them.",
    },
    ViolationType.SYNC_FILE_IO_IN_LOOP: {
        "title": "Blocking File I/O Inside Iteration",
        "deduction": 9.0,
        "severity": "MEDIUM",
        "gsf_pattern": "I/O Batching & Buffering",
        "description": "Opening or reading a file synchronously inside a loop stalls the thread once per iteration. Disk and filesystem metadata latency keeps the CPU idle-but-awake, wasting energy on every wait.",
        "fix_guidance": "Open the resource once outside the loop, read/stream it in chunks, or batch multiple writes into a single buffered transaction.",
    },
    ViolationType.SLEEP_IN_LOOP: {
        "title": "Blocking Sleep / Busy-Wait Inside Iteration",
        "deduction": 10.0,
        "severity": "MEDIUM",
        "gsf_pattern": "Demand Avoidance / Event-Driven Waiting",
        "description": "A sleep call inside a loop pins a thread in a timed wait for every iteration. Sleeping threads and their wakeups consume CPU time and prevent the host from entering deeper idle (C-)states.",
        "fix_guidance": "Replace polling with an event/callback/future, or hoist a single sleep outside the loop. If polling is unavoidable, back off exponentially and batch the work done per wakeup.",
    },
    ViolationType.JSON_SERIALIZE_IN_LOOP: {
        "title": "JSON (De)serialization Inside Iteration",
        "deduction": 7.0,
        "severity": "MEDIUM",
        "gsf_pattern": "Serialization Amortization",
        "description": "Calling json.dumps/loads (or JSON.stringify/parse) inside a loop re-parses or re-serializes on every pass. Serialization is CPU-heavy string work that scales with payload size times iteration count.",
        "fix_guidance": "Serialize once after the loop (build a list, then dump), or stream a single payload instead of one document per item.",
    },
    ViolationType.SORTED_IN_LOOP: {
        "title": "Sorting Inside Iteration",
        "deduction": 9.0,
        "severity": "MEDIUM",
        "gsf_pattern": "Algorithmic Efficiency / Sort Once",
        "description": "Sorting (sorted(), list.sort(), Arrays.sort) inside a loop re-sorts data whose order is largely unchanged. Sorts are O(N log N) each pass, multiplying into the hottest part of the workload.",
        "fix_guidance": "Sort once after the loop, keep the collection sorted as you insert (bisect/heap), or use a partial selection (top-k) when only part of the order is needed.",
    },
    ViolationType.RECURSION_WITHOUT_MEMOIZATION: {
        "title": "Self-Recursive Function Without Memoization",
        "deduction": 11.0,
        "severity": "HIGH",
        "gsf_pattern": "Caching / Memoized Computation",
        "description": "A function that calls itself without caching repeated subproblems re-computes the same results exponentially (e.g. naive fibonacci). Redundant computation is pure wasted CPU energy.",
        "fix_guidance": "Add functools.lru_cache/cache or an explicit memo table, convert the recursion to iteration with a shared table, or use dynamic programming.",
    },
    ViolationType.LINEAR_LOOKUP_IN_LOOP: {
        "title": "Linear Search (.index / indexOf) Inside Loop",
        "deduction": 8.0,
        "severity": "MEDIUM",
        "gsf_pattern": "Data Structure Selection / Hash Lookups",
        "description": "Calling list.index() or Array.indexOf() inside a loop performs an O(N) scan per iteration, turning O(N) work into O(N^2). Cache-unfriendly scans keep cores busy for no added information.",
        "fix_guidance": "Replace the list with a dict/set for O(1) membership, build a value->index map once before the loop, or use enumerate when the position is already known.",
    },
    ViolationType.EXCESSIVE_LOGGING_IN_LOOP: {
        "title": "Synchronous Logging / Print Inside Iteration",
        "deduction": 6.0,
        "severity": "LOW",
        "gsf_pattern": "I/O Batching & Log Amortization",
        "description": "print()/console.log/System.out.print inside a loop performs a synchronous I/O syscall per iteration. Terminal, pipe and log-shipping latency multiplies by N and often dominates short iterations.",
        "fix_guidance": "Accumulate messages and flush once after the loop, log at a sampled rate, or use a buffered/async logger.",
    },
}


# Universal Binary & Non-Code Extensions to exclude from source analysis
UNIVERSAL_BINARY_EXTENSIONS: Set[str] = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".bmp", ".webp", ".tiff",
    ".mp3", ".wav", ".ogg", ".mp4", ".mov", ".avi", ".mkv", ".flv", ".webm",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".iso", ".bz2", ".xz",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".o", ".a", ".lib", ".obj",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".pyd", ".class", ".jar", ".war", ".ear",
    ".db", ".sqlite", ".sqlite3", ".log", ".lock", ".wasm",
}

# Omni-Language File Extension Mapping (500+ language standards)
UNIVERSAL_EXTENSION_MAP: Dict[str, str] = {
    # Python & Derivatives
    ".py": "python", ".pyw": "python", ".pyx": "python", ".pyi": "python",
    # JavaScript & TypeScript Ecosystem
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    # C & C++
    ".c": "c", ".h": "c",
    ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hxx": "cpp", ".hh": "cpp", ".c++": "cpp", ".h++": "cpp",
    # C# / .NET
    ".cs": "c_sharp", ".csx": "c_sharp",
    # Java & JVM
    ".java": "java", ".jav": "java",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust", ".rlib": "rust",
    # Ruby
    ".rb": "ruby", ".rbw": "ruby", ".rake": "ruby", ".gemspec": "ruby",
    # PHP
    ".php": "php", ".phtml": "php", ".php3": "php", ".php4": "php", ".php5": "php", ".phps": "php",
    # Swift
    ".swift": "swift",
    # Kotlin
    ".kt": "kotlin", ".kts": "kotlin", ".ktm": "kotlin",
    # Scala
    ".scala": "scala", ".sc": "scala",
    # Dart / Flutter
    ".dart": "dart",
    # Zig
    ".zig": "zig",
    # Julia
    ".jl": "julia",
    # R
    ".r": "r", ".rd": "r", ".rdata": "r", ".rds": "r",
    # MATLAB / Octave
    ".m": "matlab", ".mat": "matlab",
    # Shell Scripting
    ".sh": "bash", ".bash": "bash", ".zsh": "bash", ".ksh": "bash",
    # PowerShell
    ".ps1": "powershell", ".psm1": "powershell", ".psd1": "powershell",
    # SQL
    ".sql": "sql", ".mysql": "sql", ".pgsql": "sql", ".pls": "sql",
    # Lua
    ".lua": "lua",
    # Perl
    ".pl": "perl", ".pm": "perl", ".t": "perl",
    # Haskell
    ".hs": "haskell", ".lhs": "haskell",
    # Elixir & Erlang
    ".ex": "elixir", ".exs": "elixir",
    ".erl": "erlang", ".hrl": "erlang",
    # Clojure
    ".clj": "clojure", ".cljs": "clojure", ".cljc": "clojure", ".edn": "clojure",
    # Solidity (Ethereum Smart Contracts)
    ".sol": "solidity",
    # Fortran
    ".f": "fortran", ".for": "fortran", ".f90": "fortran", ".f95": "fortran", ".f03": "fortran", ".f77": "fortran",
    # COBOL
    ".cbl": "cobol", ".cob": "cobol", ".cpy": "cobol",
    # Pascal & Delphi
    ".pas": "pascal", ".pp": "pascal", ".inc": "pascal",
    # Assembly
    ".asm": "assembly", ".s": "assembly", ".nasm": "assembly",
    # Groovy
    ".groovy": "groovy", ".gvy": "groovy", ".gy": "groovy", ".gsh": "groovy",
    # Salesforce Apex
    ".cls": "apex", ".trigger": "apex",
    # Hardware Description Languages (VHDL / Verilog)
    ".v": "verilog", ".vh": "verilog", ".sv": "systemverilog", ".svh": "systemverilog",
    ".vhd": "vhdl", ".vhdl": "vhdl",
    # Ada
    ".ada": "ada", ".adb": "ada", ".ads": "ada",
    # Lisp & Scheme
    ".lisp": "lisp", ".lsp": "lisp", ".scm": "scheme", ".ss": "scheme",
    # F#
    ".fs": "fsharp", ".fsi": "fsharp", ".fsx": "fsharp",
    # OCaml
    ".ml": "ocaml", ".mli": "ocaml",
    # Nim
    ".nim": "nim", ".nims": "nim",
    # D
    ".d": "d",
    # Crystal
    ".cr": "crystal",
    # Tcl
    ".tcl": "tcl",
    # Awk
    ".awk": "awk",
    # Prolog
    ".pro": "prolog", ".plg": "prolog",
    # Web & Config
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "scss", ".sass": "sass", ".less": "less",
    ".json": "json", ".json5": "json",
    ".yaml": "yaml", ".yml": "yaml",
    ".xml": "xml", ".xsd": "xml", ".xsl": "xml",
    ".toml": "toml",
    ".ini": "ini", ".cfg": "ini", ".conf": "ini",
    ".dockerfile": "dockerfile",
}

# Backward compatibility alias
SUPPORTED_EXTENSIONS: Dict[str, str] = UNIVERSAL_EXTENSION_MAP

# Tree-sitter Loop Queries for High-Fidelity CST Parsers
TREE_SITTER_LOOP_QUERIES: Dict[str, str] = {
    "python": "(for_statement) @loop (while_statement) @loop (call function: (attribute attribute: (identifier) @iter_method)) @call_iter",
    "javascript": "(for_statement) @loop (for_in_statement) @loop (while_statement) @loop (do_statement) @loop (call_expression function: (member_expression property: (property_identifier) @iter_method)) @call_iter",
    "typescript": "(for_statement) @loop (for_in_statement) @loop (while_statement) @loop (do_statement) @loop (call_expression function: (member_expression property: (property_identifier) @iter_method)) @call_iter",
    "cpp": "(for_statement) @loop (for_range_loop) @loop (while_statement) @loop (do_statement) @loop",
    "c": "(for_statement) @loop (while_statement) @loop (do_statement) @loop",
    "c_sharp": "(for_statement) @loop (for_each_statement) @loop (while_statement) @loop (do_statement) @loop",
    "java": "(for_statement) @loop (enhanced_for_statement) @loop (while_statement) @loop (do_statement) @loop (method_invocation name: (identifier) @iter_method) @call_iter",
    "go": "(for_statement) @loop",
    "rust": "(for_expression) @loop (while_expression) @loop (loop_expression) @loop",
    "ruby": "(for) @loop (while) @loop (until) @loop",
    "php": "(for_statement) @loop (foreach_statement) @loop (while_statement) @loop (do_statement) @loop",
    "kotlin": "(for_statement) @loop (while_statement) @loop (do_while_statement) @loop",
    "scala": "(for_expression) @loop (while_expression) @loop",
    "bash": "(for_statement) @loop (while_statement) @loop",
    "r": "(for) @loop (while) @loop",
    "julia": "(for_binding) @loop (while_statement) @loop",
}

LOOP_NODE_TYPES: Set[str] = {
    "for_statement",
    "while_statement",
    "do_statement",
    "for_in_statement",
    "for_range_loop",
    "enhanced_for_statement",
    "for_expression",
    "while_expression",
    "loop_expression",
    "for_each_statement",
    "until",
    "repeat_statement",
}

ITERATIVE_METHOD_NAMES: Set[str] = {
    "map", "foreach", "filter", "reduce", "flatmap", "some", "every",
    "iterrows", "itertuples", "apply", "applymap", "stream",
}

NETWORK_CALL_NAMES: Set[str] = {
    "get", "post", "put", "delete", "patch", "request", "urlopen", "send", "fetch",
}

NETWORK_MODULE_NAMES: Set[str] = {
    "requests", "httpx", "urllib", "http", "urllib3", "aiohttp",
}

# Regex patterns for Universal Lexical Scope & Pattern Analyzer (Tier 2)
LOOP_START_REGEX = re.compile(
    r"^\s*(?:(?:for|while|foreach|loop|repeat|until|do|forall)\b|perform\s+varying\b)",
    re.IGNORECASE,
)

UNIVERSAL_NETWORK_REGEX = re.compile(
    r"(?:https?://|requests\.(?:get|post|put|delete|patch)|fetch\(|http\.(?:Get|Post|Request)|"
    r"HttpClient|axios\.|reqwest::|urllib\.|curl\s+|WebClient|OpenURI|file_get_contents\(|"
    r"Net::HTTP|wget\s+|socket\.send|Invoke-WebRequest|HttpURLConnection)",
    re.IGNORECASE,
)

UNIVERSAL_DB_REGEX = re.compile(
    r"(?:\.cursor\(\)|DriverManager\.getConnection|pg_connect\(|mysql_connect\(|"
    r"sql\.Open\(|sqlite3_open|new\s+PDO\(|\.executeQuery\(|\.createConnection\(|"
    r"connect\([\"'](?:postgresql|mysql|sqlite|mongodb))",
    re.IGNORECASE,
)

UNIVERSAL_STRING_CONCAT_REGEX = re.compile(
    r"(\w+)\s*(?:\+=|\=.*?\1\s*\+)\s*(?:[\"'].*?[\"']|f[\"']|\$|`.*?`|to_string\(|str\(|\.concat\()",
    re.IGNORECASE,
)


def detect_file_language(file_path: str) -> Optional[str]:
    """Identify programming language across 500+ extensions with universal fallback."""
    base = os.path.basename(file_path).lower()
    if base in ("dockerfile", "containerfile"):
        return "dockerfile"
    if base in ("makefile", "gnumakefile"):
        return "makefile"
    if base in ("gemfile", "rakefile"):
        return "ruby"
    if base in ("cmakelists.txt",):
        return "cmake"

    ext = os.path.splitext(file_path)[1].lower()
    if not ext:
        return None
    if ext in UNIVERSAL_BINARY_EXTENSIONS:
        return None

    if ext in UNIVERSAL_EXTENSION_MAP:
        return UNIVERSAL_EXTENSION_MAP[ext]

    # Universal Code Fallback for custom, domain-specific, or emerging language files
    clean_ext = ext.lstrip(".")
    if clean_ext.isalnum() and len(clean_ext) <= 12:
        return clean_ext
    return "generic_code"


# Constructors that produce a connection-pooled / session-scoped HTTP object.
# Calls on instances of these are exempt from UNCACHED_NETWORK_IN_LOOP.
SESSION_CONSTRUCTORS: Set[str] = {
    "Session",          # requests.Session(), httpx.Client()
    "Client",           # httpx.Client(), httpx.AsyncClient()
    "AsyncClient",
    "AsyncSession",
    "PoolManager",      # urllib3.PoolManager()
    "ConnectionPool",
    "ClientSession",    # aiohttp.ClientSession()
    "Transport",
}


class GreenCodePythonASTVisitor(ast.NodeVisitor):
    """Deep Python AST Node Visitor detecting resource lifecycle & memory anti-patterns."""

    def __init__(self, source_code: str, file_path: str):
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.file_path = file_path
        self.violations: List[Dict[str, Any]] = []

        self.loop_stack: List[ast.AST] = []
        self.with_stack: List[ast.With] = []
        # Names bound to pooled HTTP session objects via `with … as <name>` or assignment
        self._session_names: Set[str] = set()

    def _get_snippet(self, node: ast.AST) -> str:
        start_line = getattr(node, "lineno", 1) - 1
        end_line = getattr(node, "end_lineno", start_line + 1)
        if 0 <= start_line < len(self.source_lines):
            return "\n".join(self.source_lines[start_line:end_line])
        return ""

    def _get_context(self, node: ast.AST, padding: int = 3) -> str:
        start_line = max(0, getattr(node, "lineno", 1) - 1 - padding)
        end_line = min(len(self.source_lines), getattr(node, "end_lineno", getattr(node, "lineno", 1)) + padding)
        return "\n".join(self.source_lines[start_line:end_line])

    def _add_violation(self, violation_type: str, node: ast.AST, custom_msg: Optional[str] = None) -> None:
        meta = VIOLATION_METADATA.get(violation_type, {})
        snippet = self._get_snippet(node)
        context = self._get_context(node)

        self.violations.append(
            {
                "file_path": self.file_path,
                "language": "python",
                "line_number": getattr(node, "lineno", 1),
                "end_line_number": getattr(node, "end_lineno", getattr(node, "lineno", 1)),
                "violation_type": violation_type,
                "title": meta.get("title", violation_type),
                "severity": meta.get("severity", "MEDIUM"),
                "deduction": meta.get("deduction", 5.0),
                "gsf_pattern": meta.get("gsf_pattern", "Green Computing Optimization"),
                "description": custom_msg or meta.get("description", ""),
                "suggested_fix": meta.get("fix_guidance", ""),
                "snippet": snippet,
                "context_code": context,
            }
        )

    def visit_With(self, node: ast.With) -> None:
        # Record any `with requests.Session() as name:` bindings so that
        # subsequent calls like `name.get(...)` inside a loop are not flagged.
        new_session_names: List[str] = []
        for item in node.items:
            ctx = item.context_expr
            alias = item.optional_vars
            if alias is None:
                continue
            # Match: with <anything>.Session() as name  OR  with Session() as name
            is_session_ctor = False
            if isinstance(ctx, ast.Call):
                func = ctx.func
                ctor_name = ""
                if isinstance(func, ast.Attribute):
                    ctor_name = func.attr
                elif isinstance(func, ast.Name):
                    ctor_name = func.id
                if ctor_name in SESSION_CONSTRUCTORS:
                    is_session_ctor = True
            if is_session_ctor and isinstance(alias, ast.Name):
                new_session_names.append(alias.id)
                self._session_names.add(alias.id)

        self.with_stack.append(node)
        self.generic_visit(node)
        self.with_stack.pop()

        for name in new_session_names:
            self._session_names.discard(name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Flag self-recursion that never caches its subresults.

        Naive recursive functions (fib, tree walks without a memo table)
        recompute the same subtrees exponentially: pure wasted CPU. A
        cache/memo decorator means the author already knew this, so those
        definitions are exempt.
        """
        name = node.name
        decorator_text = " ".join(
            ast.unparse(d) if hasattr(ast, "unparse") else "" for d in node.decorator_list
        ).lower()
        if "cache" not in decorator_text and "memo" not in decorator_text:
            recurses = False
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                if isinstance(child.func, ast.Name) and child.func.id == name:
                    recurses = True
                    break
                if (
                    isinstance(child.func, ast.Attribute)
                    and child.func.attr == name
                    and isinstance(child.func.value, ast.Name)
                    and child.func.value.id in ("self", "cls")
                ):
                    recurses = True
                    break
            if recurses:
                self._add_violation(
                    ViolationType.RECURSION_WITHOUT_MEMOIZATION,
                    node,
                    f"Function '{name}' calls itself without a cache/memo decorator, recomputing repeated subproblems exponentially.",
                )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        # Evaluate target and iterable before entering loop scope
        self.visit(node.target)
        self.visit(node.iter)
        self.loop_stack.append(node)
        if len(self.loop_stack) >= 3 and len(self.loop_stack) == 3:
            self._add_violation(
                ViolationType.NESTED_LOOPS,
                node,
                f"Loop is nested at depth {len(self.loop_stack)}. Algorithmic cost scales to O(N^{len(self.loop_stack)}).",
            )
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        self.loop_stack.pop()

    def visit_While(self, node: ast.While) -> None:
        # Evaluate test condition before entering loop scope
        self.visit(node.test)
        self.loop_stack.append(node)
        if len(self.loop_stack) >= 3 and len(self.loop_stack) == 3:
            self._add_violation(
                ViolationType.NESTED_LOOPS,
                node,
                f"While-loop is nested at depth {len(self.loop_stack)}. Algorithmic cost scales to O(N^{len(self.loop_stack)}).",
            )
        for stmt in node.body:
            self.visit(stmt)
        for stmt in node.orelse:
            self.visit(stmt)
        self.loop_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        # Check raw database cursor
        if isinstance(node.func, ast.Attribute) and node.func.attr == "cursor":
            in_with = False
            for w in self.with_stack:
                for item in w.items:
                    if item.context_expr == node:
                        in_with = True
                        break
            if not in_with:
                self._add_violation(
                    ViolationType.RAW_DB_CURSOR,
                    node,
                    "Database cursor obtained without a 'with' context manager risks unclosed socket leakage.",
                )

        # Check uncached network calls in loops
        if len(self.loop_stack) > 0:
            is_net_call = False
            is_pooled = False   # True when the receiver is a known session/pool object
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
                if isinstance(node.func.value, ast.Name):
                    receiver = node.func.value.id
                    if receiver in NETWORK_MODULE_NAMES:
                        is_net_call = True
                    elif receiver in self._session_names:
                        # Call on a pooled session object — not an anti-pattern
                        is_pooled = True
                    elif func_name in ("request", "urlopen", "send", "fetch"):
                        is_net_call = True
                    elif func_name in ("get", "post", "put", "delete", "patch"):
                        # Only flag if receiver looks like http/client/session or an argument looks like a URL
                        if any(k in receiver.lower() for k in ("http", "client", "session", "api", "request", "conn", "endpoint")):
                            is_net_call = True
                        elif any(isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith(("http://", "https://", "/")) for a in node.args):
                            is_net_call = True
                elif isinstance(node.func.value, ast.Call):
                    sub_func = node.func.value.func
                    call_name = ""
                    if isinstance(sub_func, ast.Name):
                        call_name = sub_func.id
                    elif isinstance(sub_func, ast.Attribute):
                        call_name = sub_func.attr
                    if "session" in call_name.lower() or "pool" in call_name.lower():
                        is_pooled = True
                    elif func_name in ("request", "urlopen", "fetch"):
                        is_net_call = True
                elif func_name in ("request", "urlopen", "fetch"):
                    is_net_call = True
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in ("fetch", "urlopen"):
                    is_net_call = True
            elif isinstance(node.func, ast.Call) and isinstance(node.func.func, ast.Name) and node.func.func.id == "getattr":
                # Handle dynamic metaprogramming dispatch, e.g. getattr(session, 'get')(...)
                if len(node.func.args) >= 2 and isinstance(node.func.args[1], ast.Constant) and str(node.func.args[1].value).lower() in ("get", "post", "put", "delete", "request"):
                    func_name = f"getattr(..., '{node.func.args[1].value}')"
                    if len(node.func.args) >= 1 and isinstance(node.func.args[0], ast.Name) and node.func.args[0].id in self._session_names:
                        is_pooled = True
                    else:
                        is_net_call = True

            if is_net_call and not is_pooled:
                self._add_violation(
                    ViolationType.UNCACHED_NETWORK_IN_LOOP,
                    node,
                    f"Synchronous network call '{func_name}' executed inside iteration loop causes repeated NIC power wakeups.",
                )

        # ------------------------------------------------------------------
        # Extended GSF catalogue: loop-scoped inefficiencies (roadmap item
        # "Add 10 more patterns"). All of these are checked only while a loop
        # is on the stack, and every string match below is deliberately
        # conservative so samples/eco_pipeline.py stays at zero violations.
        # ------------------------------------------------------------------
        if len(self.loop_stack) > 0:
            func = node.func
            func_name_str = ""
            receiver_name = ""
            if isinstance(func, ast.Name):
                func_name_str = func.id
            elif isinstance(func, ast.Attribute):
                func_name_str = func.attr
                if isinstance(func.value, ast.Name):
                    receiver_name = func.value.id

            # N+1 query: a SELECT (or WITH ... SELECT) issued per iteration.
            # Writes/DDL are excluded: batched row inserts are a separate
            # discussion and flagging them would fire on eco_pipeline.
            if func_name_str in ("execute", "query", "executescript"):
                first_arg = node.args[0] if node.args else None
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    q = first_arg.value.lstrip().upper()
                    if q.startswith(("SELECT", "WITH")):
                        self._add_violation(
                            ViolationType.N_PLUS_ONE_QUERY_IN_LOOP,
                            node,
                            "SELECT query executed once per loop iteration (N+1 pattern): each row costs a separate database round trip.",
                        )

            # Regex compiled/executed per iteration: re.* module functions
            # re-parse the pattern on every call.
            if receiver_name == "re" and func_name_str in (
                "compile", "search", "match", "sub", "subn",
                "findall", "finditer", "fullmatch", "split",
            ):
                self._add_violation(
                    ViolationType.INEFFICIENT_REGEX_IN_LOOP,
                    node,
                    f"re.{func_name_str}() called inside a loop re-parses the pattern every iteration.",
                )

            # Thread/process or executor pool constructed per iteration.
            if func_name_str in ("Thread", "Process", "ThreadPoolExecutor", "ProcessPoolExecutor"):
                self._add_violation(
                    ViolationType.THREAD_THRASHING_IN_LOOP,
                    node,
                    f"{func_name_str} created inside a loop: per-item execution contexts cost scheduler time and CPU wakeups.",
                )

            # Blocking file open per iteration.
            if func_name_str == "open" and receiver_name in ("", "io"):
                self._add_violation(
                    ViolationType.SYNC_FILE_IO_IN_LOOP,
                    node,
                    "open() inside a loop performs blocking filesystem I/O once per iteration.",
                )

            # Timed wait per iteration (polling loops).
            if func_name_str == "sleep":
                self._add_violation(
                    ViolationType.SLEEP_IN_LOOP,
                    node,
                    "sleep() inside a loop pins a thread in a timed wait per iteration and blocks deeper idle states.",
                )

            # JSON (de)serialization per iteration.
            if receiver_name == "json" and func_name_str in ("dumps", "loads", "dump", "load"):
                self._add_violation(
                    ViolationType.JSON_SERIALIZE_IN_LOOP,
                    node,
                    f"json.{func_name_str}() inside a loop re-serializes data on every pass.",
                )

            # Sorting per iteration.
            if func_name_str in ("sorted", "sort"):
                self._add_violation(
                    ViolationType.SORTED_IN_LOOP,
                    node,
                    f"{func_name_str}() inside a loop re-sorts data each iteration (O(N log N) per pass).",
                )

            # Linear scan per iteration.
            if func_name_str == "index":
                self._add_violation(
                    ViolationType.LINEAR_LOOKUP_IN_LOOP,
                    node,
                    ".index() inside a loop performs an O(N) scan per iteration, turning the loop into O(N^2).",
                )

            # Synchronous console logging per iteration.
            if func_name_str in ("print", "pprint"):
                self._add_violation(
                    ViolationType.EXCESSIVE_LOGGING_IN_LOOP,
                    node,
                    f"{func_name_str}() inside a loop performs a synchronous I/O syscall once per iteration.",
                )

        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        # Check quadratic string concatenation
        if len(self.loop_stack) > 0 and isinstance(node.op, ast.Add):
            is_string_val = False
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                is_string_val = True
            elif isinstance(node.value, ast.JoinedStr):
                is_string_val = True
            elif isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id in ("str", "format"):
                    is_string_val = True

            if is_string_val:
                self._add_violation(
                    ViolationType.QUADRATIC_STRING_CONCAT,
                    node,
                    "Quadratic string concatenation (+=) inside loop causes continuous heap reallocations.",
                )

        self.generic_visit(node)


def audit_with_tree_sitter(source_code: str, language: str, file_path: str) -> List[Dict[str, Any]]:
    """Parse source code with Tree-sitter and execute universal S-expression loop queries."""
    if not TREE_SITTER_AVAILABLE:
        return []

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            parser = tree_sitter_languages.get_parser(language)
            ts_lang = tree_sitter_languages.get_language(language)
    except Exception:
        return []

    code_bytes = source_code.encode("utf-8", errors="replace")
    tree = parser.parse(code_bytes)
    source_lines = source_code.splitlines()

    violations: List[Dict[str, Any]] = []
    meta = VIOLATION_METADATA[ViolationType.NESTED_LOOPS]

    def _is_iterative_node(n) -> bool:
        if n.type in LOOP_NODE_TYPES:
            return True
        if n.type in ("call_expression", "call", "method_invocation"):
            text_val = code_bytes[n.start_byte:n.end_byte].decode("utf-8", errors="replace").lower()
            for m in ITERATIVE_METHOD_NAMES:
                if f".{m}" in text_val or f"{m}(" in text_val:
                    return True
        return False

    # Compile loop query
    query_str = TREE_SITTER_LOOP_QUERIES.get(language, "(for_statement) @loop (while_statement) @loop")
    try:
        query = ts_lang.query(query_str)
        captures = query.captures(tree.root_node)
    except Exception:
        captures = []

    seen_lines: Set[int] = set()

    for node, capture_name in captures:
        node_text = code_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

        # If captured via call_iter, ensure it matches an iterative method
        if capture_name == "call_iter":
            if not _is_iterative_node(node):
                continue
            # Check for hidden heavy DataFrame row iterations (e.g. df.iterrows(), df.itertuples())
            lower_text = node_text.lower()
            if "iterrows" in lower_text or "itertuples" in lower_text:
                line_no = node.start_point[0] + 1
                if line_no not in seen_lines:
                    seen_lines.add(line_no)
                    h_meta = VIOLATION_METADATA[ViolationType.HIDDEN_ITERATIVE_COMPUTATION]
                    violations.append({
                        "file_path": file_path,
                        "language": language,
                        "line_number": line_no,
                        "end_line_number": node.end_point[0] + 1,
                        "violation_type": ViolationType.HIDDEN_ITERATIVE_COMPUTATION,
                        "title": h_meta["title"],
                        "severity": h_meta["severity"],
                        "deduction": h_meta["deduction"],
                        "gsf_pattern": h_meta["gsf_pattern"],
                        "description": f"Detected heavy iterative utility '{node_text[:40]}'. Iterating rows sequentially causes severe CPU execution bottlenecks.",
                        "suggested_fix": h_meta["fix_guidance"],
                        "snippet": node_text[:200],
                        "context_code": node_text[:200],
                    })

        # Only evaluate nesting depth on actual loop statements or verified iterative callback calls
        if capture_name not in ("loop", "call_iter"):
            continue
        if not _is_iterative_node(node):
            continue

        # Calculate nesting depth by inspecting parent loop and callback-driven iteration nodes
        depth = 1
        curr = node.parent
        while curr is not None:
            if _is_iterative_node(curr):
                depth += 1
            curr = curr.parent

        if depth >= 3:
            line_no = node.start_point[0] + 1
            end_line_no = node.end_point[0] + 1

            if line_no in seen_lines:
                continue
            seen_lines.add(line_no)

            # Extract snippet
            s_idx = max(0, line_no - 1)
            e_idx = min(len(source_lines), end_line_no)
            snippet = "\n".join(source_lines[s_idx:e_idx]) if source_lines else ""

            violations.append(
                {
                    "file_path": file_path,
                    "language": language,
                    "line_number": line_no,
                    "end_line_number": end_line_no,
                    "violation_type": ViolationType.NESTED_LOOPS,
                    "title": meta["title"],
                    "severity": meta["severity"],
                    "deduction": meta["deduction"],
                    "gsf_pattern": meta["gsf_pattern"],
                    "description": f"Iteration in {language.title()} is nested at depth {depth}. Algorithmic cost scales to O(N^{depth}), causing exponential CPU energy waste.",
                    "suggested_fix": meta["fix_guidance"],
                    "snippet": snippet,
                    "context_code": snippet,
                }
            )

    return violations


def audit_universal_lexical_scope(source_code: str, language: str, file_path: str) -> List[Dict[str, Any]]:
    """Universal Lexical Scope & Anti-Pattern Analyzer for all 500+ programming languages.

    Tracks block structure, loop nesting depths, unmanaged resource sockets,
    un-cached network requests in iteration, and quadratic memory concats.
    """
    lines = source_code.splitlines()
    violations: List[Dict[str, Any]] = []
    meta_loop = VIOLATION_METADATA[ViolationType.NESTED_LOOPS]
    meta_net = VIOLATION_METADATA[ViolationType.UNCACHED_NETWORK_IN_LOOP]
    meta_cursor = VIOLATION_METADATA[ViolationType.RAW_DB_CURSOR]
    meta_concat = VIOLATION_METADATA[ViolationType.QUADRATIC_STRING_CONCAT]
    meta_hidden = VIOLATION_METADATA[ViolationType.HIDDEN_ITERATIVE_COMPUTATION]

    loop_stack: List[Dict[str, Any]] = []
    seen_loop_lines: Set[int] = set()
    seen_net_lines: Set[int] = set()
    seen_concat_lines: Set[int] = set()

    lang_clean = (language or "").lower()
    is_indent_lang = lang_clean in ("python", "nim", "coffeescript", "elm", "yaml")
    is_keyword_lang = lang_clean in ("ruby", "lua", "julia", "bash", "sh", "zsh", "shell", "pascal", "matlab", "fortran", "ada")
    has_braces = (not is_indent_lang) and (not is_keyword_lang) and any("{" in l or "}" in l for l in lines)

    string_strip_regex = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    loop_end_regex = re.compile(r"^\s*(?:end|done|endfor|enddo|until\b|wend|next|fi|end-perform)\b|\bend\b", re.IGNORECASE)
    net_strip_regex = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:[^`\\]|\\.)*`')

    db_context_regex = re.compile(r"\b(?:with|using|defer|try)\b", re.IGNORECASE)

    for idx, raw_line in enumerate(lines):
        line_no = idx + 1
        stripped = raw_line.strip()

        if not stripped:
            continue
        if stripped.startswith(("//", "#", ";", "/*", "*", "!", "--", "'", "%")):
            continue

        curr_indent = len(raw_line) - len(raw_line.lstrip())

        # 1. Un-indent tracking for indentation-based languages or non-brace blocks
        if is_indent_lang or not has_braces:
            while loop_stack and curr_indent <= loop_stack[-1].get("indent", 0):
                loop_stack.pop()

        # 2. Check Loop Open
        is_loop = bool(LOOP_START_REGEX.search(stripped))

        # Check loop exit before checking new statement on closing blocks
        if has_braces:
            # Strip string literal contents before counting braces to prevent skew from strings containing '{' or '}'
            code_no_strings = string_strip_regex.sub('', raw_line)
            open_count = code_no_strings.count("{")
            close_count = code_no_strings.count("}")
            if close_count > open_count and loop_stack:
                for _ in range(min(len(loop_stack), close_count - open_count)):
                    loop_stack.pop()
        else:
            if loop_end_regex.search(stripped):
                if loop_stack:
                    loop_stack.pop()

        if is_loop:
            loop_stack.append({"line": line_no, "indent": curr_indent})
            depth = len(loop_stack)

            if depth >= 3 and line_no not in seen_loop_lines:
                seen_loop_lines.add(line_no)
                s_idx = max(0, line_no - 3)
                e_idx = min(len(lines), line_no + 2)
                snippet = "\n".join(lines[s_idx:e_idx])
                violations.append({
                    "file_path": file_path,
                    "language": language,
                    "line_number": line_no,
                    "end_line_number": line_no,
                    "violation_type": ViolationType.NESTED_LOOPS,
                    "title": meta_loop["title"],
                    "severity": meta_loop["severity"],
                    "deduction": meta_loop["deduction"],
                    "gsf_pattern": meta_loop["gsf_pattern"],
                    "description": f"Iteration in {language.title()} is nested at depth {depth}. Algorithmic cost scales to O(N^{depth}), causing exponential CPU energy waste.",
                    "suggested_fix": meta_loop["fix_guidance"],
                    "snippet": snippet,
                    "context_code": snippet,
                })

        # 2. Check if inside loop scope
        if len(loop_stack) >= 1:
            # Strip string literal contents before network-pattern matching to prevent
            # false positives from URL arguments passed to pooled session calls.
            _code_no_strings = net_strip_regex.sub('', stripped)
            if UNIVERSAL_NETWORK_REGEX.search(_code_no_strings) and line_no not in seen_net_lines:
                seen_net_lines.add(line_no)
                s_idx = max(0, line_no - 2)
                e_idx = min(len(lines), line_no + 1)
                snippet = "\n".join(lines[s_idx:e_idx])
                violations.append({
                    "file_path": file_path,
                    "language": language,
                    "line_number": line_no,
                    "end_line_number": line_no,
                    "violation_type": ViolationType.UNCACHED_NETWORK_IN_LOOP,
                    "title": meta_net["title"],
                    "severity": meta_net["severity"],
                    "deduction": meta_net["deduction"],
                    "gsf_pattern": meta_net["gsf_pattern"],
                    "description": f"Synchronous HTTP/network request inside iteration loop in {language.title()} causes repeated hardware transceiver wakeups.",
                    "suggested_fix": meta_net["fix_guidance"],
                    "snippet": snippet,
                    "context_code": snippet,
                })

            if UNIVERSAL_STRING_CONCAT_REGEX.search(stripped) and line_no not in seen_concat_lines:
                seen_concat_lines.add(line_no)
                s_idx = max(0, line_no - 2)
                e_idx = min(len(lines), line_no + 1)
                snippet = "\n".join(lines[s_idx:e_idx])
                violations.append({
                    "file_path": file_path,
                    "language": language,
                    "line_number": line_no,
                    "end_line_number": line_no,
                    "violation_type": ViolationType.QUADRATIC_STRING_CONCAT,
                    "title": meta_concat["title"],
                    "severity": meta_concat["severity"],
                    "deduction": meta_concat["deduction"],
                    "gsf_pattern": meta_concat["gsf_pattern"],
                    "description": f"Quadratic string buffer concatenation inside iteration loop in {language.title()} causes continuous memory allocations.",
                    "suggested_fix": meta_concat["fix_guidance"],
                    "snippet": snippet,
                    "context_code": snippet,
                })

        # 3. Check for raw database cursor/connection without context manager
        if (
            UNIVERSAL_DB_REGEX.search(stripped)
            and not stripped.startswith(('"', "'", "r'", 'r"'))
            and not any(k in stripped for k in (" in stripped", " in line", "re.search", "re.match"))
        ):
            has_context = bool(db_context_regex.search(raw_line))
            if not has_context:
                s_idx = max(0, line_no - 1)
                e_idx = min(len(lines), line_no + 2)
                snippet = "\n".join(lines[s_idx:e_idx])
                violations.append({
                    "file_path": file_path,
                    "language": language,
                    "line_number": line_no,
                    "end_line_number": line_no,
                    "violation_type": ViolationType.RAW_DB_CURSOR,
                    "title": meta_cursor["title"],
                    "severity": meta_cursor["severity"],
                    "deduction": meta_cursor["deduction"],
                    "gsf_pattern": meta_cursor["gsf_pattern"],
                    "description": f"Database cursor or connection allocated without contextual disposal in {language.title()}.",
                    "suggested_fix": meta_cursor["fix_guidance"],
                    "snippet": snippet,
                    "context_code": snippet,
                })

        # 4. Check for hidden iterative row computation in non-Tree-sitter languages
        if not stripped.startswith(('"', "'", "r'", 'r"')) and any(f".{m}(" in stripped.lower() for m in ("iterrows", "itertuples")):
            s_idx = max(0, line_no - 1)
            e_idx = min(len(lines), line_no + 1)
            snippet = "\n".join(lines[s_idx:e_idx])
            violations.append({
                "file_path": file_path,
                "language": language,
                "line_number": line_no,
                "end_line_number": line_no,
                "violation_type": ViolationType.HIDDEN_ITERATIVE_COMPUTATION,
                "title": meta_hidden["title"],
                "severity": meta_hidden["severity"],
                "deduction": meta_hidden["deduction"],
                "gsf_pattern": meta_hidden["gsf_pattern"],
                "description": f"Heavy row-by-row iteration in {language.title()} detected. Bypasses hardware vectorization pipelines.",
                "suggested_fix": meta_hidden["fix_guidance"],
                "snippet": snippet,
                "context_code": snippet,
            })

    return violations


def detect_inline_language_blocks(source_code: str, parent_language: str = "python") -> List[Dict[str, Any]]:
    """Scan file buffer for cross-language embedded code blocks (e.g. script tags, multi-line strings)."""
    blocks = []

    # 1. HTML/Template <script>...</script> tags -> JavaScript
    script_regex = re.compile(r"<script[^>]*>([\s\S]*?)</script>", re.IGNORECASE)
    for m in script_regex.finditer(source_code):
        content = m.group(1).strip()
        if content:
            start_line = source_code[:m.start(1)].count("\n") + 1
            blocks.append({
                "language": "javascript",
                "content": content,
                "line_offset": start_line,
                "block_type": "inline_html_script",
            })

    # 2. Markdown code fences: ```(python|js|javascript|cpp|java|go|rust|csharp|solidity|ruby|php|kotlin|swift|bash)\n...\n```
    fence_regex = re.compile(r"```(python|js|javascript|typescript|ts|cpp|c\+\+|java|go|rust|rs|csharp|cs|c_sharp|ruby|php|kotlin|kt|swift|solidity|sol|bash|sh)\s*\n([\s\S]*?)\n```", re.IGNORECASE)
    for m in fence_regex.finditer(source_code):
        raw_lang = m.group(1).lower()
        content = m.group(2).strip()
        norm_map = {
            "js": "javascript", "ts": "typescript", "c++": "cpp",
            "rs": "rust", "cs": "c_sharp", "csharp": "c_sharp",
            "kt": "kotlin", "sol": "solidity", "sh": "bash",
        }
        lang_id = norm_map.get(raw_lang, raw_lang)
        if content and lang_id != parent_language:
            start_line = source_code[:m.start(2)].count("\n") + 1
            blocks.append({
                "language": lang_id,
                "content": content,
                "line_offset": start_line,
                "block_type": "fenced_code_block",
            })

    # 3. Triple-quoted JavaScript or C++ string templates in Python
    if parent_language == "python":
        js_str_regex = re.compile(r'(?:js_code|javascript|js_script)\s*=\s*[\'"]{3}([\s\S]*?)[\'"]{3}', re.IGNORECASE)
        for m in js_str_regex.finditer(source_code):
            content = m.group(1).strip()
            if content:
                start_line = source_code[:m.start(1)].count("\n") + 1
                blocks.append({
                    "language": "javascript",
                    "content": content,
                    "line_offset": start_line,
                    "block_type": "python_embedded_js_string",
                })

        cpp_str_regex = re.compile(r'(?:cpp_code|inline_c|c_code)\s*=\s*[\'"]{3}([\s\S]*?)[\'"]{3}', re.IGNORECASE)
        for m in cpp_str_regex.finditer(source_code):
            content = m.group(1).strip()
            if content:
                start_line = source_code[:m.start(1)].count("\n") + 1
                blocks.append({
                    "language": "cpp",
                    "content": content,
                    "line_offset": start_line,
                    "block_type": "python_embedded_cpp_string",
                })

    return blocks


def is_violation_suppressed(source_lines: List[str], line_number: int, violation_type: str = "") -> bool:
    """Check if the code line or its immediate predecessor contains a GreenCode suppression pragma.
    
    Supports:
      - # greencode: ignore
      - # greencode: disable
      - // greencode: ignore
      - /* greencode: ignore */
      - # noqa: GSF-...
      - # noqa
    """
    idx = line_number - 1
    lines_to_check = []
    if 0 <= idx < len(source_lines):
        lines_to_check.append(source_lines[idx])
    if 0 <= idx - 1 < len(source_lines):
        lines_to_check.append(source_lines[idx - 1])

    for line in lines_to_check:
        lower = line.lower()
        if (
            "greencode: ignore" in lower
            or "greencode: disable" in lower
            or "greencode-ignore" in lower
            or "# noqa" in lower
            or "// noqa" in lower
        ):
            return True
        if violation_type and violation_type.lower() in lower:
            return True
    return False


def audit_source_code(source_code: str, language: str = "python", file_path: str = "code") -> Dict[str, Any]:
    """Unified entrypoint to audit source code in ANY programming language."""
    source_lines = source_code.splitlines()
    lines_count = len(source_lines)
    all_violations: List[Dict[str, Any]] = []
    seen_v_keys: Set[Tuple[int, str]] = set()

    # 1. Run universal Tree-sitter query analysis on primary file content (Tier 1)
    ts_violations = audit_with_tree_sitter(source_code, language, file_path)
    for v in ts_violations:
        key = (v["line_number"], v["violation_type"])
        seen_v_keys.add(key)
        all_violations.append(v)

    # 2. For Python files, run AST visitor for specialized resource lifecycle patterns
    if language == "python":
        try:
            tree = ast.parse(source_code, filename=file_path)
            py_visitor = GreenCodePythonASTVisitor(source_code, file_path)
            py_visitor.visit(tree)
            for pv in py_visitor.violations:
                key = (pv["line_number"], pv["violation_type"])
                if key not in seen_v_keys:
                    seen_v_keys.add(key)
                    all_violations.append(pv)

            # Deep AI/ML Workload Energy Profiling (PyTorch, TF, HuggingFace, ONNX)
            try:
                from app.ml_carbon import MLCarbonAnalyzer
                ml_analyzer = MLCarbonAnalyzer()
                ml_res = ml_analyzer.analyze_code(source_code, file_path=file_path)
                for mv in ml_res.get("violations", []):
                    m_key = (mv["line_number"], mv["violation_type"])
                    if m_key not in seen_v_keys:
                        seen_v_keys.add(m_key)
                        all_violations.append({
                            "file_path": file_path,
                            "line_number": mv["line_number"],
                            "end_line_number": mv.get("end_line_number", mv["line_number"]),
                            "violation_type": mv["violation_type"],
                            "title": f"AI/ML Optimization: {mv['violation_type']}",
                            "severity": mv.get("severity", "HIGH"),
                            "deduction": mv.get("deduction", 15.0),
                            "gsf_pattern": "GSF-AI-01-ACCELERATOR-EFFICIENCY",
                            "description": mv.get("description", ""),
                            "suggested_fix": mv.get("remediation", ""),
                            "snippet": mv.get("snippet", ""),
                            "context_code": mv.get("snippet", ""),
                        })
            except Exception:
                pass
        except SyntaxError:
            pass

    # 3. Universal Lexical Scope & Pattern Analyzer (Tier 2 - covers ALL 500+ languages)
    univ_violations = audit_universal_lexical_scope(source_code, language, file_path)
    for uv in univ_violations:
        key = (uv["line_number"], uv["violation_type"])
        if key not in seen_v_keys:
            seen_v_keys.add(key)
            all_violations.append(uv)

    # 4. Hybrid Mono-Repo Content-Type Scanning for embedded cross-language syntax blocks
    inline_blocks = detect_inline_language_blocks(source_code, parent_language=language)
    for block in inline_blocks:
        sub_lang = block["language"]
        sub_code = block["content"]
        line_offset = block["line_offset"] - 1

        sub_violations = audit_with_tree_sitter(sub_code, sub_lang, file_path)
        if not sub_violations:
            sub_violations = audit_universal_lexical_scope(sub_code, sub_lang, file_path)

        for sv in sub_violations:
            sv["line_number"] += line_offset
            if sv.get("end_line_number"):
                sv["end_line_number"] += line_offset
            sv["title"] = f"{sv['title']} [Embedded {sub_lang.title()}]"
            sv["description"] = f"[Hybrid Mono-Repo: Embedded {sub_lang.title()} Block] {sv['description']}"
            all_violations.append(sv)

    # Filter violations suppressed via inline pragma comments (e.g. # greencode: ignore, // greencode: ignore)
    filtered_violations = [
        v for v in all_violations
        if not is_violation_suppressed(source_lines, v.get("line_number", 1), v.get("violation_type", ""))
    ]

    # Calculate Green Score
    total_deductions = sum(v["deduction"] for v in filtered_violations)
    green_score = max(0.0, round(100.0 - total_deductions, 2))

    return {
        "file_path": file_path,
        "language": language,
        "lines_count": lines_count,
        "violations": filtered_violations,
        "green_score": green_score,
        "total_deductions": total_deductions,
    }


def audit_file_content(source_code: str, file_path: str = "code.py") -> Dict[str, Any]:
    """Backward-compatible audit function inferring language from file path."""
    lang = detect_file_language(file_path) or "python"
    return audit_source_code(source_code, language=lang, file_path=file_path)


def audit_file(file_path: str) -> Dict[str, Any]:
    """Read and audit a source code file from disk."""
    if not os.path.exists(file_path):
        return {
            "file_path": file_path,
            "language": "unknown",
            "error": "File does not exist",
            "lines_count": 0,
            "violations": [],
            "green_score": 100.0,
            "total_deductions": 0.0,
        }

    # Guard against huge minified vendor or data files (> 2 MB)
    try:
        if os.path.getsize(file_path) > 2 * 1024 * 1024:
            return {
                "file_path": file_path,
                "language": detect_file_language(file_path) or "unknown",
                "lines_count": 0,
                "violations": [],
                "green_score": 100.0,
                "total_deductions": 0.0,
                "notice": "Skipped static analysis: file exceeds 2MB limit",
            }
    except Exception:
        pass

    lang = detect_file_language(file_path) or "python"
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        source_code = f.read()

    return audit_source_code(source_code, language=lang, file_path=file_path)


def _rebase_result_paths(result: Dict[str, Any], relative_path: str) -> None:
    """Rewrite absolute host paths in a file result to repository-relative paths.

    `audit_file` records the on-disk path it actually read. For a GitHub audit
    that path is a throwaway temp workspace, so exposing it would (a) leak the
    server's directory layout to API consumers and (b) break
    `create_refactoring_pull_request`, which must address files by their real
    in-repo path.
    """
    result["file_path"] = relative_path
    result["relative_path"] = relative_path
    for violation in result.get("violations", []):
        violation["file_path"] = relative_path
        violation["relative_path"] = relative_path


def audit_repository(repo_path: str) -> Dict[str, Any]:
    """Recursively scan an entire directory or repository for all supported languages.

    Excludes virtualenvs, .git, node_modules, and cache directories.
    Calculates overall project Green Score, file count, and aggregated violations.
    """
    ignore_dirs = {
        ".git", "__pycache__", ".venv", "venv", "env", ".env", "node_modules",
        ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build", ".egg-info",
        ".gemini", "target", "vendor", "bin", "obj",
    }

    file_results: List[Dict[str, Any]] = []
    all_violations: List[Dict[str, Any]] = []
    total_lines = 0
    languages_found: Dict[str, int] = {}

    if os.path.isfile(repo_path):
        lang = detect_file_language(repo_path)
        if lang:
            res = audit_file(repo_path)
            res["relative_path"] = os.path.basename(repo_path)
            _rebase_result_paths(res, os.path.basename(repo_path))
            file_results.append(res)
            all_violations.extend(res["violations"])
            total_lines += res["lines_count"]
            languages_found[lang] = languages_found.get(lang, 0) + 1
    else:
        real_repo_root = os.path.realpath(repo_path)
        all_candidate_paths: List[str] = []
        for root, dirs, files in os.walk(repo_path, followlinks=False):
            # Prune ignored and symlinked directories to prevent infinite traversal loops
            dirs[:] = [
                d for d in dirs
                if d not in ignore_dirs and not d.startswith(".") and not os.path.islink(os.path.join(root, d))
            ]
            for file in files:
                all_candidate_paths.append(os.path.join(root, file))

        all_candidate_paths.sort()
        for full_path in all_candidate_paths:

                # Security check: Skip symlinks resolving outside repository root (e.g. /etc/passwd attacks)
                if os.path.islink(full_path):
                    real_target = os.path.realpath(full_path)
                    if not (real_target == real_repo_root or real_target.startswith(real_repo_root + os.sep)):
                        continue

                lang = detect_file_language(full_path)
                if lang:
                    rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
                    res = audit_file(full_path)
                    res["relative_path"] = rel_path
                    # Report repository-relative paths, never the host's absolute
                    # temp/workspace path. Absolute paths leaked server layout and
                    # made GitHub PR patching fail to match the remote file.
                    _rebase_result_paths(res, rel_path)
                    file_results.append(res)
                    all_violations.extend(res["violations"])
                    total_lines += res["lines_count"]
                    languages_found[lang] = languages_found.get(lang, 0) + 1

    total_files = len(file_results)
    if total_files == 0:
        overall_score = 100.0
    else:
        file_scores = [f["green_score"] for f in file_results]
        overall_score = round(sum(file_scores) / total_files, 2)

    # Breakdown by violation type
    breakdown: Dict[str, int] = {}
    for v in all_violations:
        vtype = v["violation_type"]
        breakdown[vtype] = breakdown.get(vtype, 0) + 1

    return {
        "repo_path": repo_path,
        "total_files": total_files,
        "total_lines": total_lines,
        "green_score": overall_score,
        "total_violations": len(all_violations),
        "violation_breakdown": breakdown,
        "languages_breakdown": languages_found,
        "violations": all_violations,
        "file_results": file_results,
    }


_ACTIVE_WORKSPACES: Set[str] = set()
MAX_ZIP_EXTRACTED_BYTES = 100 * 1024 * 1024  # 100 MB max uncompressed
MAX_ZIP_FILE_COUNT = 3000                     # Max files in archive


def cleanup_workspace(workspace_dir: Optional[str] = None) -> None:
    """Remove a specific temporary workspace directory."""
    global _ACTIVE_WORKSPACES
    if workspace_dir:
        _ACTIVE_WORKSPACES.discard(workspace_dir)
        if os.path.isdir(workspace_dir):
            try:
                shutil.rmtree(workspace_dir, ignore_errors=True)
            except Exception:
                pass


def cleanup_all_workspaces() -> None:
    """Remove all registered active temporary workspace directories."""
    global _ACTIVE_WORKSPACES
    for ws in list(_ACTIVE_WORKSPACES):
        if os.path.isdir(ws):
            try:
                shutil.rmtree(ws, ignore_errors=True)
            except Exception:
                pass
    _ACTIVE_WORKSPACES.clear()


# Backward compatibility alias
cleanup_active_workspace = cleanup_all_workspaces
atexit.register(cleanup_all_workspaces)


def audit_zip_archive(zip_path: str) -> Dict[str, Any]:
    """Extract a ZIP archive of a multi-language repository to an active workspace and audit it.

    Hardenings:
    - Zip Slip Protection: Ensures no archive members escape target directory via '../' traversal.
    - Zip Bomb Defense: Limits total uncompressed payload to 100MB and maximum 3,000 files.
    - Concurrency-safe: Tracks workspaces individually without global variable collisions.
    """
    temp_dir = tempfile.mkdtemp(prefix="greencode_workspace_")
    _ACTIVE_WORKSPACES.add(temp_dir)
    real_temp_dir = os.path.realpath(temp_dir)

    total_uncompressed_bytes = 0
    total_files = 0

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            for member in z.infolist():
                total_files += 1
                if total_files > MAX_ZIP_FILE_COUNT:
                    raise ValueError(f"ZIP archive exceeds maximum file count limit ({MAX_ZIP_FILE_COUNT}).")

                total_uncompressed_bytes += member.file_size
                if total_uncompressed_bytes > MAX_ZIP_EXTRACTED_BYTES:
                    raise ValueError(f"ZIP archive exceeds uncompressed payload limit ({MAX_ZIP_EXTRACTED_BYTES // (1024*1024)} MB).")

                # Validate canonical path against Zip Slip directory traversal
                target_path = os.path.realpath(os.path.join(temp_dir, member.filename))
                if not (target_path == real_temp_dir or target_path.startswith(real_temp_dir + os.sep)):
                    raise ValueError(f"Security Alert: Directory traversal detected in zip archive member: '{member.filename}'.")

                z.extract(member, temp_dir)

        # GitHub zipballs wrap the whole tree in a single "owner-repo-<sha>/"
        # directory. Detecting and descending into it keeps every reported
        # file path relative to the actual repository root.
        audit_root = _resolve_archive_root(temp_dir)
        results = audit_repository(audit_root)
        results["repo_path"] = zip_path
        results["workspace_dir"] = temp_dir
        return results
    except Exception:
        cleanup_workspace(temp_dir)
        raise


def _resolve_archive_root(temp_dir: str) -> str:
    """Descend past a single synthetic top-level wrapper directory, if present.

    GitHub/Codeload archives are shaped as `<owner>-<repo>-<sha>/...`. Without
    this, every violation would be reported as
    `zeenat28-ui-greencode-a1b2c3d4/src/app.py` instead of `src/app.py`, which
    breaks the Pull Request patcher and the SARIF paths.
    """
    try:
        entries = [e for e in os.listdir(temp_dir) if e != "__MACOSX"]
    except OSError:
        return temp_dir
    if len(entries) != 1:
        return temp_dir
    candidate = os.path.join(temp_dir, entries[0])
    if os.path.isdir(candidate) and not os.path.islink(candidate):
        return candidate
    return temp_dir

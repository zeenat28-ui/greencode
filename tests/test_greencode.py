"""Automated Test Suite for GreenCode Auditor.

Tests AST static analysis, dynamic profiling calculations, Electricity Maps integration,
GreenCode AI Synthesizer refactoring, and database persistence.
"""

import os
import sys
import unittest

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import (
    get_cumulative_carbon_savings,
    get_latest_repositories,
    get_repository_details,
    init_db,
    save_profile_metric,
    save_refactoring_record,
    save_scan_results,
)
from app.optimizer import (
    get_zone_carbon_intensity,
    list_available_zones,
    refactor_repository_code,
)
from app.parser import (
    ViolationType,
    audit_file,
    audit_file_content,
    audit_repository,
)
from app.profiler import DynamicExecutionProfiler, calculate_energy_and_sci


class TestGreenCodeAuditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_ast_parser_detects_all_four_antipatterns(self):
        """Verify AST visitor detects nested loops, unmanaged cursors, network in loop, and string concat."""
        heavy_sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "heavy_pipeline.py"))
        result = audit_file(heavy_sample_path)

        self.assertEqual(result["file_path"], heavy_sample_path)
        violations = result["violations"]
        self.assertGreater(len(violations), 0)

        v_types = {v["violation_type"] for v in violations}
        self.assertIn(ViolationType.NESTED_LOOPS, v_types, "Failed to detect nested loops (depth >= 3)")
        self.assertIn(ViolationType.RAW_DB_CURSOR, v_types, "Failed to detect unmanaged raw DB cursor")
        self.assertIn(ViolationType.UNCACHED_NETWORK_IN_LOOP, v_types, "Failed to detect uncached network call in loop")
        self.assertIn(ViolationType.QUADRATIC_STRING_CONCAT, v_types, "Failed to detect quadratic string addition")

        # Green score must be deducted significantly
        self.assertLess(result["green_score"], 75.0)
        self.assertGreaterEqual(result["green_score"], 0.0)

    def test_02_ast_parser_eco_pipeline_has_zero_violations(self):
        """Verify optimized eco pipeline passes with 100/100 score."""
        eco_sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "eco_pipeline.py"))
        result = audit_file(eco_sample_path)

        self.assertEqual(len(result["violations"]), 0, f"Expected 0 violations, found: {result['violations']}")
        self.assertEqual(result["green_score"], 100.0)

    def test_03_repository_audit(self):
        """Verify repository-level traversal and score aggregation."""
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        repo_result = audit_repository(samples_dir)

        self.assertGreaterEqual(repo_result["total_files"], 2)
        self.assertTrue(0.0 <= repo_result["green_score"] <= 100.0)
        self.assertIn("violation_breakdown", repo_result)

    def test_04_energy_and_sci_calculation(self):
        """Verify GSF SCI mathematical model calculations."""
        metrics = calculate_energy_and_sci(
            duration_sec=2.5,
            avg_cpu_percent=40.0,
            peak_memory_mb=128.0,
            grid_intensity=215.0,  # California ISO
        )

        self.assertGreater(metrics["total_power_watts"], 0)
        self.assertGreater(metrics["energy_joules"], 0)
        self.assertGreater(metrics["energy_wh"], 0)
        self.assertGreater(metrics["operational_carbon_gco2"], 0)
        self.assertGreater(metrics["sci_score_gco2"], 0)

    def test_05_dynamic_profiler_execution(self):
        """Verify dynamic execution profiler generates complete telemetry without crashing."""
        profiler = DynamicExecutionProfiler(grid_intensity_gco2_per_kwh=300.0)
        eco_sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "eco_pipeline.py"))

        res = profiler.profile_file(eco_sample_path, timeout_sec=10.0)
        self.assertIn(res.profiling_mode, ["DOCKER_ISOLATED", "HOST_SANDBOX_FALLBACK"])
        self.assertGreater(res.duration_sec, 0)
        self.assertGreaterEqual(res.peak_memory_mb, 0)
        self.assertGreater(res.energy_wh, 0)
        self.assertGreater(res.sci_score_gco2, 0)

    def test_06_electricity_maps_zones(self):
        """Verify regional grid intensity lookup and fallback data integrity."""
        zones = list_available_zones()
        self.assertGreater(len(zones), 5)

        caiso = get_zone_carbon_intensity("US-CAL-CISO")
        self.assertEqual(caiso["zone"], "US-CAL-CISO")
        self.assertGreater(caiso["carbon_intensity"], 0)

        de = get_zone_carbon_intensity("DE")
        self.assertEqual(de["zone"], "DE")

    def test_07_greencode_refactoring_synthesis(self):
        """Verify GreenCode AI Synthesizer refactoring engine on all 4 violation types."""
        test_cases = [
            ("NESTED_LOOPS_DEPTH_3+", "for a in x:\n    for b in y:\n        for c in z:\n            val = a+b+c"),
            ("RAW_DB_CURSOR_NO_CONTEXT", "conn = sqlite3.connect(':memory:')\ncursor = conn.cursor()\ncursor.execute('SELECT 1')"),
            ("UNCACHED_NETWORK_IN_LOOP", "for i in range(10):\n    requests.get('http://api')"),
            ("QUADRATIC_STRING_CONCAT_IN_LOOP", "msg = ''\nfor row in data:\n    msg += row"),
        ]

        for v_type, snippet in test_cases:
            refactored = refactor_repository_code(snippet, v_type)
            self.assertIn("refactored_code", refactored)
            self.assertGreater(refactored["energy_reduction_pct"], 0)
            self.assertGreater(refactored["carbon_saved_gco2_10k_runs"], 0)
            self.assertNotEqual(refactored["refactored_code"], snippet)

    def test_08_database_crud(self):
        """Verify SQLite DB persistence of scans, profiles, and refactoring records."""
        repo = save_scan_results(
            name="TestWorkspace",
            path_or_url="/test/path",
            total_files=3,
            total_lines=150,
            green_score=85.0,
            violations_data=[
                {
                    "file_path": "test.py",
                    "line_number": 12,
                    "violation_type": "NESTED_LOOPS_DEPTH_3+",
                    "severity": "HIGH",
                    "deduction": 15.0,
                    "snippet": "for i in range(10): pass",
                    "suggested_fix": "Flatten loops",
                }
            ],
        )
        self.assertIsNotNone(repo.id)

        details = get_repository_details(repo.id)
        self.assertEqual(details["name"], "TestWorkspace")
        self.assertEqual(len(details["violations"]), 1)

        metric = save_profile_metric(
            file_path="test.py",
            duration_sec=1.2,
            avg_cpu_percent=35.0,
            peak_memory_mb=45.0,
            energy_wh=0.015,
            operational_carbon_gco2=0.003,
            sci_score=0.0035,
            repo_id=repo.id,
        )
        self.assertIsNotNone(metric.id)

        refact = save_refactoring_record(
            original_code="bad",
            refactored_code="good",
            energy_reduction_pct=50.0,
            carbon_saved_gco2_10k_runs=30.0,
        )
        self.assertIsNotNone(refact.id)

        savings = get_cumulative_carbon_savings()
        self.assertGreater(savings["total_carbon_saved_gco2_10k_runs"], 0)

    def test_09_multilanguage_treesitter_parsing(self):
        """Verify Tree-sitter correctly parses JS, C++, Java, and Go, detecting nested loops."""
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        
        lang_samples = {
            "javascript": "sample_nested.js",
            "cpp": "sample_nested.cpp",
            "java": "sample_nested.java",
            "go": "sample_nested.go",
        }
        
        for lang_id, filename in lang_samples.items():
            filepath = os.path.join(samples_dir, filename)
            self.assertTrue(os.path.exists(filepath), f"Missing test sample: {filepath}")
            
            result = audit_file(filepath)
            self.assertEqual(result["language"], lang_id)
            self.assertGreater(len(result["violations"]), 0, f"Expected nested loop violation in {filename}")
            
            v_types = [v["violation_type"] for v in result["violations"]]
            self.assertIn(ViolationType.NESTED_LOOPS, v_types)
            self.assertLess(result["green_score"], 100.0)

    def test_10_multilanguage_refactoring(self):
        """Verify GreenCode AI Synthesizer multi-language refactoring synthesis for non-Python targets."""
        for lang_id in ["javascript", "cpp", "java", "go"]:
            bad_code = "for (int i=0; i<10; i++) { for (int j=0; j<10; j++) { for (int k=0; k<10; k++) {} } }"
            refactored = refactor_repository_code(
                bad_snippet=bad_code,
                violation_type=ViolationType.NESTED_LOOPS,
                language_id=lang_id,
            )
            self.assertIn("refactored_code", refactored)
            self.assertGreater(refactored["energy_reduction_pct"], 0)
            self.assertGreater(refactored["carbon_saved_gco2_10k_runs"], 0)
            self.assertTrue(refactored.get("model_used"))

    def test_11_async_database_connection_pool(self):
        """Verify asynchronous connection pooling, transaction retries, and async CRUD operations."""
        import asyncio
        from app.database import (
            init_async_db,
            save_scan_results_async,
            get_latest_repositories_async,
            get_cumulative_carbon_savings_async,
        )

        async def run_async_db_test():
            await init_async_db()
            repo_res = await save_scan_results_async(
                name="AsyncTestRepo",
                path_or_url="/async/test/path",
                total_files=5,
                total_lines=300,
                green_score=88.5,
                violations_data=[{
                    "file_path": "async.js",
                    "line_number": 10,
                    "violation_type": "NESTED_LOOPS_DEPTH_3+",
                    "deduction": 15.0,
                }],
            )
            self.assertIsNotNone(repo_res["id"])
            repos = await get_latest_repositories_async(limit=5)
            self.assertGreaterEqual(len(repos), 1)
            savings = await get_cumulative_carbon_savings_async()
            self.assertIn("total_carbon_saved_gco2_10k_runs", savings)

        asyncio.run(run_async_db_test())

    def test_12_advanced_iterative_syntax_queries(self):
        """Verify Tree-sitter advanced queries catching callback iterations and DataFrame row loops."""
        from app.parser import audit_source_code

        # Test A: JS callback-driven nested iterations (map inside forEach inside for)
        js_code = "for (let i = 0; i < 10; i++) { items.forEach(async (item) => { item.list.map(x => x * 2); }); }"
        res_js = audit_source_code(js_code, "javascript")
        v_types_js = [v["violation_type"] for v in res_js["violations"]]
        self.assertIn(ViolationType.NESTED_LOOPS, v_types_js)

        # Test B: Python DataFrame row iterations (df.iterrows())
        py_code = "import pandas as pd\ndf = pd.DataFrame()\nfor idx, row in df.iterrows(): pass"
        res_py = audit_source_code(py_code, "python")
        v_types_py = [v["violation_type"] for v in res_py["violations"]]
        self.assertIn(ViolationType.HIDDEN_ITERATIVE_COMPUTATION, v_types_py)

    def test_13_resilient_geographic_telemetry_fallbacks(self):
        """Verify resilient geographic fallback matrix activation under rate-limits / network timeouts."""
        from app.optimizer import GEOGRAPHIC_FALLBACK_MATRIX

        # Must have global coverage (North America, Europe, Asia-Pacific, South America)
        self.assertGreaterEqual(len(GEOGRAPHIC_FALLBACK_MATRIX), 15)
        self.assertIn("CA-QC", GEOGRAPHIC_FALLBACK_MATRIX)
        self.assertIn("SG", GEOGRAPHIC_FALLBACK_MATRIX)

        # Verify rate-limit resilience: invalid/rate-limited token activates fallback without throwing
        fallback_res = get_zone_carbon_intensity("CA-QC", api_key="rate_limit_token_test")
        self.assertEqual(fallback_res["zone"], "CA-QC")
        self.assertGreater(fallback_res["carbon_intensity"], 0)
        self.assertIn("Fallback", fallback_res["source"])
        self.assertFalse(fallback_res["is_live"])

    def test_14_dynamic_time_of_day_carbon_shift(self):
        """Verify dynamic time-of-day marginal carbon shift calculations (solar clean bonus vs evening fossil peaker)."""
        # Test Germany (DE): UTC+1, solar peak (9-16) -> target UTC hour 11 is 12:00 local (solar peak)
        # fossil peak (18-22) -> target UTC hour 18 is 19:00 local (fossil peak)
        solar_res = get_zone_carbon_intensity("DE", target_utc_hour=11)
        self.assertEqual(solar_res["zone"], "DE")
        self.assertIn("marginal_carbon_intensity", solar_res)
        self.assertIn("time_of_day_info", solar_res)
        self.assertEqual(solar_res["time_of_day_info"]["period"], "solar_peak")
        self.assertLess(solar_res["marginal_carbon_intensity"], solar_res["carbon_intensity"])
        self.assertEqual(solar_res["time_of_day_info"]["multiplier"], 0.70)

        # Test evening fossil peak
        fossil_res = get_zone_carbon_intensity("DE", target_utc_hour=18)
        self.assertEqual(fossil_res["time_of_day_info"]["period"], "fossil_peak")
        self.assertGreater(fossil_res["marginal_carbon_intensity"], fossil_res["carbon_intensity"])
        self.assertEqual(fossil_res["time_of_day_info"]["multiplier"], 1.28)

    def test_15_async_engine_disposal_and_task_polling(self):
        """Verify async DB engine disposal and asynchronous scan task queue status polling."""
        import asyncio
        from app.database import close_async_db
        from app.tasks import enqueue_github_scan_task, get_task_status

        # Enqueue a GitHub audit. No network call happens synchronously: the
        # payload is dispatched to the broker or the in-process worker.
        queued = enqueue_github_scan_task(
            "octocat/Hello-World", token="ghp_dummytoken1234567890", user_id=1
        )
        task_id = queued.get("task_id")
        self.assertIsNotNone(task_id)
        self.assertIn(queued.get("queue_backend", ""), (
            "Celery / Redis Distributed Broker",
            "In-Process Concurrent Task Worker",
        ))

        # Polling must never raise, whatever state the task happens to be in.
        status_info = get_task_status(task_id, user_id=1)
        self.assertIn(status_info.get("status"), [
            "PENDING", "STARTED", "Processing", "Completed", "SUCCESS", "FAILURE",
        ])

        # Test close_async_db without errors
        asyncio.run(close_async_db())

    def test_16_universal_omni_language_support(self):
        """Verify universal multi-tier parsing across 500+ languages, Tree-sitter, and lexical scope analyzer."""
        from app.parser import detect_file_language, audit_source_code, ViolationType

        # Test language detection across diverse language paradigms
        test_exts = {
            "main.rs": "rust",
            "contract.sol": "solidity",
            "app.kt": "kotlin",
            "Server.cs": "c_sharp",
            "script.rb": "ruby",
            "program.pas": "pascal",
            "core.cbl": "cobol",
            "system.zig": "zig",
            "compute.jl": "julia",
            "custom_algo.xyz": "xyz",  # Arbitrary unknown extension falls back to custom language name
        }
        for fname, expected_lang in test_exts.items():
            detected = detect_file_language(fname)
            self.assertEqual(detected, expected_lang, f"Failed for filename {fname}: expected {expected_lang}, got {detected}")

        # Test Rust nested loops (Tree-sitter or Universal Lexical Scope)
        rust_code = """
        fn process(data: &Vec<Vec<Vec<i32>>>) {
            for i in 0..data.len() {
                for j in 0..data[i].len() {
                    for k in 0..data[i][j].len() {
                        println!("{}", data[i][j][k]);
                    }
                }
            }
        }
        """
        res_rs = audit_source_code(rust_code, "rust")
        v_types_rs = [v["violation_type"] for v in res_rs["violations"]]
        self.assertIn(ViolationType.NESTED_LOOPS, v_types_rs)

        # Test Solidity nested loops and raw DB/state calls
        sol_code = """
        contract EcoVault {
            function process(uint n) public {
                for (uint i = 0; i < n; i++) {
                    for (uint j = 0; j < n; j++) {
                        for (uint k = 0; k < n; k++) {
                            // High gas cost nested execution
                        }
                    }
                }
            }
        }
        """
        res_sol = audit_source_code(sol_code, "solidity")
        v_types_sol = [v["violation_type"] for v in res_sol["violations"]]
        self.assertIn(ViolationType.NESTED_LOOPS, v_types_sol)

        # Test Pascal nested loops (begin ... end block structure)
        pascal_code = """
        program PolyglotTest;
        begin
            for i := 1 to 10 do begin
                for j := 1 to 10 do begin
                    for k := 1 to 10 do begin
                        writeln(i * j * k);
                    end;
                end;
            end;
        end.
        """
        res_pas = audit_source_code(pascal_code, "pascal")
        v_types_pas = [v["violation_type"] for v in res_pas["violations"]]
        self.assertIn(ViolationType.NESTED_LOOPS, v_types_pas)

        # Test custom unknown proprietary language with nested loops
        custom_code = """
        loop outer:
            loop middle:
                loop inner:
                    compute_data()
        """
        res_custom = audit_source_code(custom_code, "custom_source")
        v_types_custom = [v["violation_type"] for v in res_custom["violations"]]
        self.assertIn(ViolationType.NESTED_LOOPS, v_types_custom)

    def test_17_real_world_eco_refactoring_synthesis(self):
        """Verify real itertools.product transformation and context manager cleanup."""
        from unittest.mock import patch
        # 1. Test Python nested loop transformation (under deterministic synthesis)
        bad_py = "for i in a:\n    for j in b:\n        for k in c:\n            val = i * j * k"
        with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "", "HF_TOKEN": ""}):
            res = refactor_repository_code(bad_py, ViolationType.NESTED_LOOPS, language_id="python")
            self.assertIn("product(a, b, c)", res["refactored_code"])
            self.assertIn("for i, j, k in", res["refactored_code"])

            # 2. Test DB cursor context manager and redundant close elimination
            bad_db = "cursor = conn.cursor()\ncursor.execute('SELECT 1')\ncursor.close()"
            res_db = refactor_repository_code(bad_db, ViolationType.RAW_DB_CURSOR, language_id="python")
            self.assertIn("with conn.cursor() as cursor:", res_db["refactored_code"])
            self.assertIn("Redundant: auto-closed", res_db["refactored_code"])

            # 3. Test JavaScript Map lookup flattening
            bad_js = "for (let i=0; i<10; i++) { for (let j=0; j<10; j++) { for (let k=0; k<10; k++) {} } }"
            res_js = refactor_repository_code(bad_js, ViolationType.NESTED_LOOPS, language_id="javascript")
            self.assertIn("Map", res_js["refactored_code"])

    def test_17b_refactored_python_must_actually_compile(self):
        """Regression: the nested-loop rewrite once emitted stray indentation.

        `_refactor_nested_loop_code` used `if not base_indent:` to capture the
        loop's base indentation. An empty string is a *legitimate* indentation
        for a top-level loop and is falsy, so the guard kept re-capturing until
        it reached the first indented line. The whole rewritten block was then
        emitted indented by four spaces, and the suggestion handed back to the
        user was an IndentationError.

        A refactor tool that returns code which does not compile is worse than
        no refactor at all, so the output is compiled here rather than merely
        pattern-matched.
        """
        from app.optimizer import _refactor_nested_loop_code

        top_level = "for a in items:\n    for b in items:\n        for c in items:\n            total += a * b * c"
        out = _refactor_nested_loop_code(top_level)
        try:
            compile("from itertools import product\n" + out, "<refactor>", "exec")
        except SyntaxError as exc:
            self.fail(f"top-level rewrite does not compile: {exc}\n{out}")

        # The emitted `for` must sit at column 0, matching the input.
        for_line = next(l for l in out.splitlines() if l.lstrip().startswith("for "))
        self.assertFalse(for_line.startswith(" "), f"stray indent on: {for_line!r}")

        # An indented fragment is only meaningful spliced into its block, so it
        # is verified in place - which is how the UI applies it.
        fragment = "\n".join([
            "    for a in items:",
            "        for b in items:",
            "            for c in items:",
            "                total += a * b * c",
        ])
        spliced = (
            "from itertools import product\ndef outer():\n"
            + _refactor_nested_loop_code(fragment)
            + "\n    return total\n"
        )
        try:
            compile(spliced, "<refactor>", "exec")
        except SyntaxError as exc:
            self.fail(f"indented fragment does not splice cleanly: {exc}")

        # And through the public entry point, which is what the API returns.
        from unittest.mock import patch
        with patch.dict(os.environ, {"HUGGINGFACE_API_KEY": "", "HF_TOKEN": ""}):
            res = refactor_repository_code(
                top_level, ViolationType.NESTED_LOOPS, language_id="python"
            )
        try:
            compile(res["refactored_code"], "<refactor>", "exec")
        except SyntaxError as exc:
            self.fail(f"public refactor output does not compile: {exc}\n{res['refactored_code']}")

    def test_17b_profiler_container_is_removed_when_start_fails(self):
        """A failed start() must not strand a container in "created" state.

        `start()` used to sit outside the removal guarantee, so any failure
        between create() and the cleanup left a container holding its memory
        and pid reservation on the host until the daemon was restarted.
        """
        from app.profiler import DynamicExecutionProfiler

        class ExplodingContainer:
            def __init__(self):
                self.removed = False

            def start(self):
                raise RuntimeError("cgroup setup failed")

            def remove(self, force=False):
                self.removed = True

        container = ExplodingContainer()

        class FakeImages:
            @staticmethod
            def get(image):
                return object()

            @staticmethod
            def pull(image):  # pragma: no cover - get() short-circuits
                return object()

        class FakeContainers:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return container

        class FakeClient:
            def __init__(self):
                self.containers = FakeContainers()
                self.images = FakeImages()

        client = FakeClient()
        profiler = DynamicExecutionProfiler(grid_intensity_gco2_per_kwh=300.0)
        profiler.docker_client = client
        profiler.connection_type = "DOCKER_ISOLATED"

        with self.assertRaises(RuntimeError):
            profiler._profile_with_docker(
                os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "eco_pipeline.py")),
                10.0, 300.0,
            )
        self.assertTrue(container.removed, "container leaked after a failed start()")
        self.assertEqual(
            client.containers.kwargs.get("labels"),
            {"com.greencode.analysis": "1"},
            "containers must be labelled so crash cleanup can find them",
        )

    def test_18_multi_language_profiler_host_detection(self):
        """Verify dynamic profiler gracefully handles diverse file extensions without Python syntax crashes."""
        profiler = DynamicExecutionProfiler(grid_intensity_gco2_per_kwh=200.0)
        import tempfile

        # Test Ruby script profiling fallback
        with tempfile.NamedTemporaryFile(suffix=".rb", mode="w", delete=False) as f:
            f.write("puts 'hello ruby'")
            rb_path = f.name

        try:
            res_rb = profiler.profile_file(rb_path, timeout_sec=2.0)
            self.assertIn(res_rb.profiling_mode, ["HOST_SANDBOX_FALLBACK", "DOCKER_ISOLATED"])
            # Must not throw Python SyntaxError or exit code crash
            self.assertIsNotNone(res_rb.duration_sec)
        finally:
            if os.path.exists(rb_path):
                os.remove(rb_path)

    def test_19_github_actions_output_generation(self):
        """Verify CLI mode writes outputs to $GITHUB_OUTPUT when running under GitHub Actions."""
        import tempfile
        from app.main import run_cli
        from unittest.mock import patch

        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w+", delete=False) as gh_out:
            gh_out_path = gh_out.name

        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        test_args = ["main.py", "--path", samples_dir, "--threshold", "50.0", "--ci"]

        try:
            with patch.dict(os.environ, {"GITHUB_OUTPUT": gh_out_path}), \
                 patch.object(sys, "argv", test_args):
                try:
                    run_cli()
                except SystemExit:
                    pass

            with open(gh_out_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("green_score=", content)
            self.assertIn("total_violations=", content)
            self.assertIn("passed=", content)
        finally:
            if os.path.exists(gh_out_path):
                os.remove(gh_out_path)

    def test_20_sarif_v210_export_compliance(self):
        """Verify OASIS SARIF v2.1.0 report generation and file persistence."""
        import tempfile
        import json
        from app.sarif import generate_sarif_report
        from app.parser import audit_repository

        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        scan_res = audit_repository(samples_dir)

        with tempfile.NamedTemporaryFile(suffix=".sarif", delete=False) as tf:
            sarif_file = tf.name

        try:
            sarif_doc = generate_sarif_report(scan_res, output_path=sarif_file, base_dir=samples_dir)
            self.assertEqual(sarif_doc.get("version"), "2.1.0")
            self.assertIn("sarif-schema-2.1.0.json", sarif_doc.get("$schema", ""))
            self.assertGreater(len(sarif_doc.get("runs", [])), 0)

            run = sarif_doc["runs"][0]
            driver = run["tool"]["driver"]
            self.assertEqual(driver["name"], "GreenCode Auditor")
            self.assertGreater(len(driver["rules"]), 0)
            self.assertGreater(len(run["results"]), 0)

            first_res = run["results"][0]
            self.assertIn("ruleId", first_res)
            self.assertIn("level", first_res)
            self.assertIn("locations", first_res)

            with open(sarif_file, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
            self.assertEqual(disk_data["version"], "2.1.0")
        finally:
            if os.path.exists(sarif_file):
                os.remove(sarif_file)

    def test_21_in_place_file_remediation_with_backup(self):
        """Verify 1-click in-place code modification creates timestamped backup and pre-validates AST."""
        import tempfile
        from app.optimizer import apply_code_fix_in_place

        original_code = (
            "def heavy_calc(items):\n"
            "    results = []\n"
            "    for i in items:\n"
            "        results.append(i * 2)\n"
            "    return results\n"
        )
        optimized_code = (
            "def heavy_calc(items):\n"
            "    return [i * 2 for i in items]\n"
        )
        invalid_code = (
            "def heavy_calc(items):\n"
            "    return [i * 2 for i in items\n"
        )

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False, encoding="utf-8") as tf:
            tf.write(original_code)
            test_file_path = tf.name

        try:
            # 1. Test invalid syntax rejection
            bad_res = apply_code_fix_in_place(test_file_path, original_code, invalid_code)
            self.assertFalse(bad_res["success"])
            self.assertIn("syntax error", bad_res["error"].lower())

            # 2. Test successful in-place replacement with backup
            good_res = apply_code_fix_in_place(test_file_path, original_code, optimized_code)
            self.assertTrue(good_res["success"])
            backup_path = good_res["backup_path"]
            self.assertTrue(os.path.exists(backup_path))

            # Verify backup has original code
            with open(backup_path, "r", encoding="utf-8") as bf:
                self.assertEqual(bf.read(), original_code)

            # Verify file now has optimized code
            with open(test_file_path, "r", encoding="utf-8") as cur_f:
                self.assertEqual(cur_f.read().strip(), optimized_code.strip())

            # Clean up backup
            if os.path.exists(backup_path):
                os.remove(backup_path)
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

    def test_21b_in_place_nested_indentation_and_ast_validation(self):
        """Verify in-place patching accurately aligns deeply indented snippets without syntax errors."""
        import ast
        import tempfile
        from app.optimizer import apply_code_fix_in_place

        file_content = (
            "import os\n"
            "\n"
            "def handle_workload(items):\n"
            "    total = 0\n"
            "    for item in items:\n"
            "        if item > 0:\n"
            "            # Deeply indented snippet (12 spaces)\n"
            "            for a in range(item):\n"
            "                for b in range(item):\n"
            "                    total += a * b\n"
            "    return total\n"
        )

        original_snippet = (
            "            for a in range(item):\n"
            "                for b in range(item):\n"
            "                    total += a * b"
        )

        # Refactored snippet at column 0 with AI markdown ticks
        ai_refactored_code = (
            "```python\n"
            "# Optimized with product\n"
            "from itertools import product\n"
            "total += sum(a * b for a, b in product(range(item), range(item)))\n"
            "```"
        )

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False, encoding="utf-8") as tf:
            tf.write(file_content)
            test_file_path = tf.name

        try:
            res = apply_code_fix_in_place(test_file_path, original_snippet, ai_refactored_code)
            self.assertTrue(res["success"], f"Failed to apply fix: {res.get('error')}")

            # Verify syntax
            with open(test_file_path, "r", encoding="utf-8") as rf:
                patched_code = rf.read()

            parsed = ast.parse(patched_code)
            self.assertIsNotNone(parsed)
            self.assertIn("def handle_workload(items):", patched_code)
            self.assertIn("return total", patched_code)
            self.assertIn("from itertools import product", patched_code)

            if "backup_path" in res and os.path.exists(res["backup_path"]):
                os.remove(res["backup_path"])
        finally:
            if os.path.exists(test_file_path):
                os.remove(test_file_path)

    def test_22_follow_the_sun_migration_advisor(self):
        """Verify Follow-the-Sun Geographic Cloud Migration calculation and recommendations."""
        from app.optimizer import calculate_region_carbon_migration_advisor

        adv = calculate_region_carbon_migration_advisor("US-VA", energy_wh=2.0, monthly_workloads=50000)
        self.assertEqual(adv["current_zone"], "US-VA")
        self.assertGreater(adv["current_intensity_gco2_per_kwh"], 0)
        self.assertGreater(adv["carbon_reduction_pct"], 0)
        self.assertGreater(adv["annual_co2_abated_kg"], 0)
        self.assertIn("recommended_zone", adv)
        self.assertGreater(len(adv["top_green_regions"]), 0)
        self.assertIn("datacenter_hubs", adv)

    def test_23_github_pr_comment_formatting(self):
        """Verify GitHub PR sticky comment builds rich GSF tables and handles HTTP posting."""
        from unittest.mock import patch, MagicMock
        from app.github_client import post_pr_carbon_comment

        dummy_scan = {
            "green_score": 62.5,
            "total_files": 4,
            "total_lines": 350,
            "violations": [
                {
                    "file_path": "samples/heavy.py",
                    "line_number": 42,
                    "title": "Cubic Loop Nesting",
                    "violation_type": "CUBIC_LOOP",
                    "deduction": 15.0,
                    "suggested_fix": "Flatten inner loop using hash map lookup.",
                }
            ],
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 98765, "html_url": "https://github.com/test/repo/issues/12#issuecomment-98765"}

        with patch("app.github_client._get_session") as mock_session:
            mock_request = mock_session.return_value.request
            mock_request.return_value = mock_resp
            res = post_pr_carbon_comment(
                repo_full_name="test/repo",
                pr_number=12,
                scan_result=dummy_scan,
                gate_threshold=70.0,
                token="ghp_dummytoken1234567890",
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["comment_id"], 98765)

            called_args, called_kwargs = mock_request.call_args
            payload = called_kwargs.get("json", {})
            body = payload.get("body", "")
            self.assertIn("GreenCode Auditor — Pull Request Carbon Quality Gate", body)
            self.assertIn("62.5 / 100.0", body)
            self.assertIn("BLOCKED", body)
            self.assertIn("Cubic Loop Nesting", body)
            self.assertIn("Green Software Foundation (GSF) Standards Reference", body)


if __name__ == "__main__":
    unittest.main()





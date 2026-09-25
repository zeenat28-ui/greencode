"""Tests for sandboxed dynamic analysis and audit intelligence planning.

The security-relevant properties are asserted explicitly: untrusted filenames
are refused, host execution is never a fallback, and archives cannot escape
their extraction directory.
"""

import os
import tempfile
import unittest
import zipfile
from unittest import mock

from app.audit_intel import analyze_repository_context, build_remediation_plan
from app.dynamic_analysis import DynamicAnalyzer, _command_for
from app.main import _repo_root, _safe_extract

SCAN = {
    "repo_path": "acme/widgets",
    "total_files": 40,
    "total_lines": 8000,
    "green_score": 72.5,
    "violations": [
        {"violation_type": "QUADRATIC_STRING", "file": "a.py", "line": 10, "snippet": "s += x"},
        {"violation_type": "QUADRATIC_STRING", "file": "a.py", "line": 20, "snippet": "s += y"},
        {"violation_type": "NESTED_LOOP", "file": "b.py", "line": 5, "snippet": "for i..."},
        {"violation_type": "MISSING_CONNECTION_POOL", "file": "c.py", "line": 7, "snippet": "req()"},
        {"violation_type": "IDLE_GPU_GAP", "file": "d.py", "line": 9, "snippet": "sync()"},
    ],
    "violation_breakdown": {
        "QUADRATIC_STRING": 2, "NESTED_LOOP": 1,
        "MISSING_CONNECTION_POOL": 1, "IDLE_GPU_GAP": 1,
    },
}


class TestEntryPointDiscovery(unittest.TestCase):
    def _make(self, names):
        d = tempfile.mkdtemp()
        for n in names:
            open(os.path.join(d, n), "w").close()
        return d

    def test_prefers_test_suite_over_main(self):
        found = DynamicAnalyzer.discover_entry_points(
            self._make(["main.py", "test_widgets.py"])
        )
        self.assertTrue(found)
        self.assertEqual(found[0][1], "test_widgets.py")
        self.assertEqual(found[0][0], "python")

    def test_falls_back_to_main(self):
        self.assertEqual(
            DynamicAnalyzer.discover_entry_points(self._make(["main.py"]))[0][1], "main.py"
        )

    def test_empty_directory_yields_nothing(self):
        self.assertEqual(DynamicAnalyzer.discover_entry_points(tempfile.mkdtemp()), [])

    def test_missing_directory_does_not_raise(self):
        self.assertEqual(
            DynamicAnalyzer.discover_entry_points("/nonexistent/path/xyz"), []
        )

    def test_directories_are_not_mistaken_for_entry_points(self):
        d = tempfile.mkdtemp()
        os.mkdir(os.path.join(d, "test_dir.py"))
        self.assertEqual(DynamicAnalyzer.discover_entry_points(d), [])


class TestCommandConstruction(unittest.TestCase):
    def test_python_command_is_positional(self):
        self.assertEqual(_command_for("python", "test_x.py")[:3],
                         ["python", "-u", "/workspace/test_x.py"])

    def test_java_class_name_is_validated(self):
        self.assertIsNone(_command_for("java", "Bad Name.java"))
        self.assertIsNotNone(_command_for("java", "Main.java"))

    def test_unknown_language_returns_none(self):
        self.assertIsNone(_command_for("cobol", "main.cbl"))


class TestSandboxPosture(unittest.TestCase):
    def test_no_docker_means_no_execution(self):
        """Host execution of untrusted code is never a fallback."""
        analyzer = DynamicAnalyzer(docker_client=None)
        with mock.patch.object(DynamicAnalyzer, "_get_client", return_value=None):
            r = analyzer.analyze(tempfile.mkdtemp(), repo_slug="a/b")
        self.assertFalse(r.ok)
        self.assertEqual(r.reason, "sandbox_unavailable")
        self.assertTrue(r.warnings)

    def test_unsafe_filename_is_refused(self):
        analyzer = DynamicAnalyzer(docker_client=object())
        d = tempfile.mkdtemp()
        open(os.path.join(d, "test_a;rm -rf b.py"), "w").close()
        with mock.patch.object(DynamicAnalyzer, "_get_client", return_value=object()):
            r = analyzer.analyze(d, repo_slug="a/b")
        self.assertFalse(r.ok)
        self.assertEqual(r.reason, "unsafe_entry_point")

    def test_no_entry_point_is_reported_clearly(self):
        analyzer = DynamicAnalyzer(docker_client=object())
        with mock.patch.object(DynamicAnalyzer, "_get_client", return_value=object()):
            r = analyzer.analyze(tempfile.mkdtemp(), repo_slug="a/b")
        self.assertFalse(r.ok)
        self.assertEqual(r.reason, "no_entry_point")

    def test_status_shape_is_stable(self):
        s = DynamicAnalyzer.status()
        for key in ("dynamic_analysis_available", "blockers", "docker",
                    "energy_measurement", "hardware_measurement_available"):
            self.assertIn(key, s)


class TestArchiveSafety(unittest.TestCase):
    def test_traversal_entry_is_rejected(self):
        d = tempfile.mkdtemp()
        evil = os.path.join(d, "evil.zip")
        with zipfile.ZipFile(evil, "w") as zf:
            zf.writestr("../../escaped.txt", "pwned")
        dest = tempfile.mkdtemp()
        with zipfile.ZipFile(evil) as zf:
            with self.assertRaises(ValueError):
                _safe_extract(zf, dest)
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(dest), "escaped.txt")))

    def test_zip_bomb_is_rejected(self):
        """The guard inspects declared uncompressed sizes before extracting.

        A real 600 MB payload would slow the suite without testing anything
        extra, so the archive's own metadata is replaced with a declared size
        that exceeds the cap. ``extractall`` must never be reached.
        """
        d = tempfile.mkdtemp()
        bomb = os.path.join(d, "bomb.zip")
        with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("small.bin", b"\0" * 16)

        dest = tempfile.mkdtemp()
        with zipfile.ZipFile(bomb) as zf:
            # Stand in for a bomb: same entry, enormous declared size.
            for info in zf.infolist():
                info.file_size = 600 * 1024 * 1024
            with self.assertRaises(ValueError) as ctx:
                _safe_extract(zf, dest)

        self.assertIn("500 MB", str(ctx.exception))
        # Nothing may have been written to disk.
        self.assertEqual(os.listdir(dest), [])

    def test_aggregate_size_limit_is_enforced(self):
        """Several individually-small entries must also trip the cap."""
        d = tempfile.mkdtemp()
        many = os.path.join(d, "many.zip")
        with zipfile.ZipFile(many, "w", zipfile.ZIP_DEFLATED) as zf:
            for i in range(20):
                zf.writestr(f"f{i}.bin", b"\0")

        dest = tempfile.mkdtemp()
        with zipfile.ZipFile(many) as zf:
            for info in zf.infolist():
                info.file_size = 40 * 1024 * 1024  # 20 * 40 MB = 800 MB
            with self.assertRaises(ValueError):
                _safe_extract(zf, dest)

    def test_normal_archive_extracts(self):
        d = tempfile.mkdtemp()
        ok = os.path.join(d, "ok.zip")
        with zipfile.ZipFile(ok, "w") as zf:
            zf.writestr("repo/main.py", "print(1)")
        dest = tempfile.mkdtemp()
        with zipfile.ZipFile(ok) as zf:
            _safe_extract(zf, dest)
        self.assertTrue(os.path.isfile(os.path.join(dest, "repo", "main.py")))


class TestRepoRoot(unittest.TestCase):
    def test_single_top_level_directory_is_unwrapped(self):
        d = tempfile.mkdtemp()
        os.mkdir(os.path.join(d, "widgets-main"))
        self.assertEqual(_repo_root(d), os.path.join(d, "widgets-main"))

    def test_flat_archive_root_is_unchanged(self):
        d = tempfile.mkdtemp()
        open(os.path.join(d, "main.py"), "w").close()
        self.assertEqual(_repo_root(d), d)


class TestAuditIntelligence(unittest.TestCase):
    def test_context_is_deterministic(self):
        self.assertEqual(analyze_repository_context(SCAN), analyze_repository_context(SCAN))

    def test_findings_are_grouped_by_theme(self):
        ctx = analyze_repository_context(SCAN)
        self.assertIn("Algorithmic complexity",
                      {t["theme"] for t in ctx["violation_themes"]})

    def test_total_violations_counted(self):
        self.assertEqual(analyze_repository_context(SCAN)["total_violations"], 5)

    def test_plan_steps_are_ranked_and_deduplicated(self):
        plan = build_remediation_plan(SCAN)["plan"]
        scores = [s["priority_score"] for s in plan["steps"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        step = next(s for s in plan["steps"] if s["violation_type"] == "QUADRATIC_STRING")
        self.assertEqual(step["occurrences"], 2)
        self.assertEqual(step["file_count"], 1)

    def test_quick_wins_exclude_high_risk(self):
        plan = build_remediation_plan(SCAN)["plan"]
        quick = [s for s in plan["steps"] if s["effort"] == "low" and s["risk"] == "low"]
        self.assertNotIn("IDLE_GPU_GAP", [s["violation_type"] for s in quick])

    def test_effort_estimate_present(self):
        eff = build_remediation_plan(SCAN)["plan"]["estimated_effort"]
        self.assertIn("engineer_days", eff)
        self.assertIn("band", eff)

    def test_empty_scan_is_handled(self):
        out = build_remediation_plan({"violations": [], "total_files": 0})
        self.assertEqual(out["plan"]["step_count"], 0)
        self.assertEqual(out["plan"]["estimated_effort"]["engineer_days"], 0.0)

        self.assertIsNone(_command_for("java", "Bad Name.java"))
        self.assertIsNotNone(_command_for("java", "Main.java"))

    def test_unknown_language_returns_none(self):
        self.assertIsNone(_command_for("cobol", "main.cbl"))

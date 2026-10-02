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


class TestContainerResultHandling(unittest.TestCase):
    """The Docker result path must be testable without a Docker daemon.

    Every other sandbox test stubs `_get_client`, so nothing ever executed the
    code between "container started" and "SCI computed". Three defects lived in
    exactly that gap and shipped unnoticed:

      * `select_meter` was called but never imported (NameError),
      * the meter was read through a `read()` method no meter implemented, so
        the RAPL branch was unreachable and the model fallback was permanent,
      * `Container.wait()` returns a mapping, and unpacking it as a pair turned
        the exit-code conversion into a ValueError that surfaced as a bogus
        "timeout" for runs that had actually succeeded.
    """

    def _finalise(self, **overrides):
        kwargs = dict(
            workdir=".", before=None, meter=None, duration=1.0, exit_code=0,
            timed_out=False, stdout_bytes=b"", stderr_bytes=b"",
            repo_slug="a/b", ref="main", entry="main.py", language="python",
            grid_intensity=280.0, functional_unit=1.0,
        )
        kwargs.update(overrides)
        return DynamicAnalyzer()._finalise(**kwargs)

    def test_01_select_meter_is_imported_and_resolvable(self):
        """`select_meter` was called inside the container path but not imported."""
        import app.dynamic_analysis as da

        self.assertTrue(hasattr(da, "select_meter"))
        meter = da.select_meter()
        self.assertTrue(meter is None or hasattr(meter, "read"))

    def test_02_no_meter_falls_back_to_model_with_a_warning(self):
        r = self._finalise(meter=None, before=None)
        self.assertEqual(r.measurement_method, "model")
        self.assertFalse(r.measurement_is_hardware)
        self.assertTrue(any("not measured" in w for w in r.warnings))
        self.assertGreater(r.it_energy_joules, 0.0)

    def test_03_rapl_reading_is_used_when_available(self):
        """A real counter delta must beat the model and be labelled as hardware."""
        from app.energy_sensors import EnergySample

        class FakeRapl:
            def __init__(self):
                self.t = 0

            def describe(self):
                return {"backend": "rapl"}

            def read(self):
                self.t += 1
                # 1 second of package energy at 10 W == 10 joules.
                return EnergySample(
                    timestamp=float(self.t),
                    per_domain_uj={"package": self.t * 10_000_000},
                )

            def joules_between(self, a, b):
                delta = (b.per_domain_uj["package"] - a.per_domain_uj["package"]) / 1e6
                return {"cpu_joules": delta, "memory_joules": 0.0, "total_joules": delta}

        meter = FakeRapl()
        r = self._finalise(meter=meter, before=meter.read(), duration=1.0)
        self.assertEqual(r.measurement_method, "rapl")
        self.assertTrue(r.measurement_is_hardware)
        self.assertAlmostEqual(r.it_energy_joules, 10.0, places=3)

    def test_04_battery_meter_is_not_treated_as_a_measurement(self):
        """A whole-system average must not masquerade as a per-run counter."""
        from app.energy_sensors import BatteryMeter

        meter = BatteryMeter.__new__(BatteryMeter)
        meter._baseline = 12.0
        self.assertIsNone(meter.read())
        r = self._finalise(meter=meter, before=None, duration=1.0)
        self.assertEqual(r.measurement_method, "model")
        self.assertFalse(r.measurement_is_hardware)

    def test_05_rapl_delta_respects_domain_precedence(self):
        """`core` is a subset of `package`; summing both would double count."""
        from app.energy_sensors import EnergySample, RaplMeter

        m = RaplMeter.__new__(RaplMeter)
        m._kinds = {"package": "package", "core": "core", "dram": "dram"}
        m._ranges = {"package": 10_000_000}
        a = EnergySample(0.0, {"package": 1_000_000, "core": 500_000, "dram": 100_000})
        b = EnergySample(1.0, {"package": 3_100_000, "core": 900_000, "dram": 300_000})
        j = m.joules_between(a, b)
        self.assertAlmostEqual(j["cpu_joules"], 2.1, places=6)
        self.assertAlmostEqual(j["memory_joules"], 0.2, places=6)
        self.assertTrue(hasattr(m, "read"))


class TestContainerWaitSemantics(unittest.TestCase):
    """`Container.wait()` returns a mapping, not a (stdout, stderr) pair.

    Unpacking it as a pair produced the dict *keys* as strings, so the exit-code
    conversion raised a ValueError and every successful run was reported as a
    timeout - the feature looked broken on any machine that actually had Docker.
    """

    class _FakeImages:
        @staticmethod
        def get(image):
            return object()

        @staticmethod
        def pull(image):  # pragma: no cover - get() short-circuits
            return object()

    class _FakeContainer:
        wait_result = None
        removed = False

        def start(self):
            pass

        def wait(self, timeout=None):
            return self.wait_result

        def logs(self, stdout=False, stderr=False, tail=None):
            return b""

        def remove(self, force=False):
            type(self).removed = True

    def _run_with(self, wait_result):
        analyzer = DynamicAnalyzer(docker_client=object())
        container = self._FakeContainer()
        container.wait_result = wait_result
        type(container).removed = False

        client = type("C", (), {
            "images": self._FakeImages,
            "containers": type(
                "CC", (), {"create": staticmethod(lambda **kw: container)})(),
        })()
        analyzer._get_client = lambda: client

        with tempfile.TemporaryDirectory() as workdir:
            open(os.path.join(workdir, "main.py"), "w").close()
            r = analyzer._run_in_container(
                client, workdir, "main.py", "python", "python:3.12-slim",
                ["python", "-u", "main.py"], 30.0, "a/b", "main", 280.0, 1.0,
            )
        return r, container

    def test_01_mapping_return_yields_status_code_and_ok(self):
        r, container = self._run_with({"StatusCode": 0, "Error": None})
        self.assertTrue(r.ok, f"clean run reported as failed: {r.reason}")
        self.assertEqual(r.reason, "ok")
        self.assertEqual(r.exit_code, 0)
        self.assertTrue(container.removed, "container must always be removed")

    def test_02_mapping_return_with_nonzero_code_is_reported(self):
        r, _ = self._run_with({"StatusCode": 2, "Error": None})
        self.assertEqual(r.exit_code, 2)
        self.assertFalse(r.ok)

    def test_03_legacy_tuple_return_is_still_accepted(self):
        r, container = self._run_with((3, "some error"))
        self.assertEqual(r.exit_code, 3)
        self.assertTrue(any("some error" in w for w in r.warnings))
        self.assertTrue(container.removed)


class TestStaleContainerReaping(unittest.TestCase):
    """A process killed between create() and cleanup must not strand containers.

    Containers are labelled so reaping can never touch an operator's own.
    """

    class _FakeContainer:
        def __init__(self, created):
            self.attrs = {"Created": created}
            self.removed = False

        def remove(self, force=False):
            self.removed = True

    class _FakeContainers:
        def __init__(self, items):
            self._items = items
            self.queried_label = None

        def list(self, all=False, filters=None):
            self.queried_label = (filters or {}).get("label")
            return list(self._items)

    def _client(self, items):
        containers = self._FakeContainers(items)
        return type("C", (), {"containers": containers})(), containers

    def test_01_created_timestamp_is_an_rfc3339_string(self):
        """Docker returns a string here; comparing it to a float silently reaped nothing."""
        self.assertAlmostEqual(
            DynamicAnalyzer._created_epoch(self._FakeContainer("2026-01-01T00:00:00Z")),
            1767225600.0, places=0,
        )

    def test_02_nanosecond_precision_is_tolerated(self):
        epoch = DynamicAnalyzer._created_epoch(
            self._FakeContainer("2026-01-01T00:00:00.123456789Z")
        )
        self.assertIsNotNone(epoch)
        self.assertAlmostEqual(epoch, 1767225600.123456, places=3)

    def test_03_unparseable_age_means_skip_not_delete(self):
        self.assertIsNone(DynamicAnalyzer._created_epoch(self._FakeContainer("nonsense")))
        self.assertIsNone(DynamicAnalyzer._created_epoch({}))

        old = self._FakeContainer("nonsense")
        client, _ = self._client([old])
        removed = DynamicAnalyzer.reap_stale_containers(client, max_age_seconds=0)
        self.assertEqual(removed, 0)
        self.assertFalse(old.removed, "unknown age must not be a licence to delete")

    def test_04_stale_is_reaped_and_fresh_is_kept(self):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).timestamp()
        old = self._FakeContainer(datetime.fromtimestamp(now - 4000, timezone.utc))
        fresh = self._FakeContainer(datetime.fromtimestamp(now, timezone.utc))
        client, containers = self._client([old, fresh])

        removed = DynamicAnalyzer.reap_stale_containers(client, max_age_seconds=900)
        self.assertEqual(removed, 1)
        self.assertTrue(old.removed)
        self.assertFalse(fresh.removed, "a running analysis must not be reaped")
        self.assertEqual(containers.queried_label, "com.greencode.analysis")

    def test_05_reaper_failure_never_breaks_an_analysis(self):
        class Exploding:
            @property
            def containers(self):
                raise RuntimeError("daemon gone")

        self.assertEqual(DynamicAnalyzer.reap_stale_containers(Exploding()), 0)


class TestScaphhandreMeter(unittest.TestCase):
    """ScaphhandreMeter reads real RAPL counters via the Scaphandre HTTP sidecar.

    All tests mock urllib.request so no network is required.  The assertions
    focus on the three things that must be true for production correctness:
      1. The regex extracts the right metric line from a Prometheus payload.
      2. Connectivity failures are silent (returns None, not an exception).
      3. joules_between() computes a correct positive delta.
      4. select_meter() prefers RAPL, then Scaphandre, never battery when both
         are present.
    """

    # Minimal Prometheus payload with a host energy counter.
    _PROM_BODY = (
        "# HELP scaph_host_energy_microjoules Host energy in microjoules\n"
        "# TYPE scaph_host_energy_microjoules counter\n"
        "scaph_host_energy_microjoules 12345678.0\n"
        "scaph_process_power_consumption_microwatts{pid=\"1\"} 500.0\n"
    )

    def _meter(self, body: str):
        """Return a ScaphhandreMeter whose HTTP call returns ``body``."""
        from app.energy_sensors import ScaphhandreMeter

        meter = ScaphhandreMeter(url="http://fake-scaphandre:8080/metrics")
        meter._ok = None  # force lazy probe

        class _FakeResponse:
            def read(self):
                return body.encode()

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse()):
            _ = meter.available  # trigger probe

        return meter

    def test_01_prometheus_body_parsed_correctly(self):
        """The regex must extract the host energy counter value."""
        from app.energy_sensors import ScaphhandreMeter

        meter = ScaphhandreMeter.__new__(ScaphhandreMeter)
        meter._url = "http://fake:8080/metrics"

        class _FakeResponse:
            def read(self):
                return self._PROM_BODY.encode()

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

        _FakeResponse._PROM_BODY = self._PROM_BODY
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse()):
            val = meter._scrape()

        self.assertIsNotNone(val)
        self.assertAlmostEqual(val, 12345678.0, places=1)

    def test_02_connection_failure_returns_none_not_exception(self):
        """An unreachable sidecar must never crash the analysis path."""
        from app.energy_sensors import ScaphhandreMeter

        meter = ScaphhandreMeter.__new__(ScaphhandreMeter)
        meter._url = "http://fake:8080/metrics"
        meter._ok = None

        import urllib.error
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = meter._scrape()

        self.assertIsNone(result)

    def test_03_available_is_false_when_sidecar_unreachable(self):
        """available must be False, not raise, when the sidecar is down."""
        from app.energy_sensors import ScaphhandreMeter

        meter = ScaphhandreMeter.__new__(ScaphhandreMeter)
        meter._url = "http://fake:8080/metrics"
        meter._ok = None

        import urllib.error
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("refused"),
        ):
            self.assertFalse(meter.available)

    def test_04_read_returns_scaphandre_point_with_correct_uj(self):
        """read() must return a ScaphandrePoint carrying the scraped value."""
        from app.energy_sensors import ScaphhandreMeter, ScaphandrePoint

        meter = ScaphhandreMeter.__new__(ScaphhandreMeter)
        meter._url = "http://fake:8080/metrics"

        class _FakeResponse:
            def read(self):
                return (
                    "scaph_host_energy_microjoules 99000000.0\n"
                ).encode()

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse()):
            point = meter.read()

        self.assertIsInstance(point, ScaphandrePoint)
        self.assertAlmostEqual(point.host_uj, 99_000_000.0, places=1)

    def test_05_joules_between_computes_correct_delta(self):
        """A 10 MJ counter increment = 10 J total, all reported as cpu_joules."""
        from app.energy_sensors import ScaphhandreMeter, ScaphandrePoint

        a = ScaphandrePoint(timestamp=0.0, host_uj=100_000_000.0)
        b = ScaphandrePoint(timestamp=1.0, host_uj=110_000_000.0)  # +10 MJ = 10 J

        j = ScaphhandreMeter.joules_between(a, b)
        self.assertAlmostEqual(j["total_joules"], 10.0, places=6)
        self.assertAlmostEqual(j["cpu_joules"], 10.0, places=6)
        self.assertAlmostEqual(j["memory_joules"], 0.0, places=6)

    def test_06_joules_between_clamps_negative_delta(self):
        """Counter resets (very rare) must not produce negative energy."""
        from app.energy_sensors import ScaphhandreMeter, ScaphandrePoint

        a = ScaphandrePoint(timestamp=0.0, host_uj=200_000_000.0)
        b = ScaphandrePoint(timestamp=1.0, host_uj=10_000.0)  # apparent reset

        j = ScaphhandreMeter.joules_between(a, b)
        self.assertGreaterEqual(j["total_joules"], 0.0)

    def test_07_select_meter_prefers_rapl_over_scaphandre(self):
        """RAPL direct access beats the HTTP sidecar tier."""
        from app.energy_sensors import RaplMeter, ScaphhandreMeter, select_meter

        fake_rapl = mock.MagicMock(spec=RaplMeter)
        fake_rapl.available = True

        with mock.patch("app.energy_sensors.RaplMeter", return_value=fake_rapl):
            meter = select_meter()

        self.assertIsInstance(meter, type(fake_rapl))

    def test_08_select_meter_falls_to_scaphandre_when_no_rapl(self):
        """When RAPL is absent, Scaphandre is chosen before battery/model."""
        from app.energy_sensors import ScaphandreMeter, select_meter

        fake_scaph = mock.MagicMock(spec=ScaphandreMeter)
        fake_scaph.available = True

        with (
            mock.patch("app.energy_sensors.RaplMeter", side_effect=RuntimeError("no rapl")),
            mock.patch("app.energy_sensors.ScaphandreMeter", return_value=fake_scaph),
        ):
            meter = select_meter()

        self.assertIsInstance(meter, type(fake_scaph))

    def test_10_select_meter_never_reports_a_backend_it_cannot_use(self):
        """`perf` brackets a command, not a counter, so it is not a meter class.

        select_meter() walks the documented tier list, but `perf` must resolve to
        None rather than being faked into an object. Returning a stub here would
        hand callers a meter whose `read()` returns nothing, and the sandbox would
        quietly fall through to the TDP model while claiming a perf measurement.
        """
        from app.energy_sensors import _instantiate_meter

        self.assertIsNone(_instantiate_meter("perf"))
        self.assertIsNone(_instantiate_meter("model"))

    def test_09_scaphandre_measurement_is_labelled_hardware_true(self):
        """Scaphandre reads real hardware; measurement_is_hardware must be True."""
        from app.energy_sensors import ScaphandrePoint

        # _finalise receives `before` (already read outside) and calls
        # meter.read() once more for the `after` snapshot. We provide a meter
        # whose single read() call returns the "after" point (+5 J).
        before_point = ScaphandrePoint(timestamp=0.0, host_uj=100_000_000.0)
        after_point = ScaphandrePoint(timestamp=1.0, host_uj=105_000_000.0)

        class FixedScaph:
            def describe(self):
                return {"backend": "scaphandre"}

            def read(self):
                # Called exactly once by _finalise for the "after" snapshot.
                return after_point

            def joules_between(self, a, b):
                delta = max(0.0, b.host_uj - a.host_uj) / 1e6
                return {"cpu_joules": delta, "memory_joules": 0.0, "total_joules": delta}

        r = DynamicAnalyzer()._finalise(
            workdir=".", before=before_point, meter=FixedScaph(), duration=1.0,
            exit_code=0, timed_out=False, stdout_bytes=b"", stderr_bytes=b"",
            repo_slug="a/b", ref="main", entry="main.py", language="python",
            grid_intensity=280.0, functional_unit=1.0,
        )
        self.assertEqual(r.measurement_method, "scaphandre")
        self.assertTrue(r.measurement_is_hardware)
        self.assertAlmostEqual(r.it_energy_joules, 5.0, places=3)



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

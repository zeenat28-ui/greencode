"""Tests for dynamic function-level energy attribution.

The tracer is exercised with a stubbed meter so attribution is deterministic.
What is under test is the correlation logic - self-time derivation, stdlib
exclusion, and recursion handling - none of which depends on real hardware.
"""

import os
import unittest
from unittest import mock

from app.energy_tracer import EnergyTracer, _is_user_frame


class _FakeMeter:
    """A meter that reports a fixed joule amount per measurement."""

    def __init__(self, joules=1.0):
        self.joules = joules
        self.backend = "rapl"
        self.reads = 0

    def measure(self, fn, *a, **k):
        fn()
        return None, 0.0, {
            "cpu_joules": self.joules,
            "memory_joules": 0.0,
            "total_joules": self.joules,
        }

    def describe(self):
        return {"backend": self.backend}


class TestFrameFiltering(unittest.TestCase):
    def test_stdlib_and_builtin_frames_are_excluded(self):
        import threading

        self.assertFalse(_is_user_frame(threading.__file__, None))
        self.assertFalse(_is_user_frame("<string>", None))
        self.assertFalse(_is_user_frame("", None))

    def test_site_packages_excluded(self):
        fake = "/usr/lib/python3.12/site-packages/numpy/core/x.py"
        self.assertFalse(_is_user_frame(fake, None))

    def test_user_file_included(self):
        self.assertTrue(_is_user_frame("/home/dev/project/main.py", None))

    def test_include_paths_narrow_the_scope(self):
        import tempfile

        proj = tempfile.mkdtemp()
        other = tempfile.mkdtemp()
        a = os.path.join(proj, "a.py")
        b = os.path.join(other, "b.py")
        self.assertTrue(_is_user_frame(a, (proj,)))
        self.assertFalse(_is_user_frame(b, (proj,)))


class TestEnergyTracer(unittest.TestCase):
    def _run(self, fn, meter=None, **kw):
        tracer = EnergyTracer(interval=0.001, **kw)
        with mock.patch("app.energy_sensors.select_meter",
                        return_value=meter or _FakeMeter()):
            return tracer.run(fn)

    @staticmethod
    def _by_name(report):
        """Map short names to hotspot records.

        ``co_qualname`` for a nested function is
        ``TestClass.test_method.<locals>.name``, so match on the final segment.
        """
        out = {}
        for h in report["hotspots"]:
            out[h["qualified_name"].rsplit(".", 1)[-1]] = h
        return out

    def test_returns_result_and_report(self):
        result, report = self._run(lambda: 6 * 7)
        self.assertEqual(result, 42)
        self.assertIn("hotspots", report)
        self.assertGreaterEqual(report["unique_functions"], 1)

    def test_workload_exceptions_are_captured_not_raised(self):
        def boom():
            raise ValueError("nope")

        result, report = self._run(boom)
        self.assertIsNone(result)
        self.assertIn("ValueError", report["error"])
        self.assertIn("nope", report["error"])

    def test_hot_function_is_ranked_first(self):
        def burn():
            total = 0
            for i in range(200_000):
                total += i * i
            return total

        _, report = self._run(burn)
        self.assertEqual(report["hotspots"][0]["qualified_name"].rsplit(".", 1)[-1], "burn")

    def test_recursion_is_counted_per_call(self):
        def fact(n):
            return 1 if n <= 1 else n * fact(n - 1)

        _, report = self._run(lambda: fact(6))
        entry = self._by_name(report)["fact"]
        # fact(6)->fact(5)->...->fact(1); the n<=1 guard stops there, so six
        # calls. Getting the stack balance wrong here would corrupt the count.
        self.assertEqual(entry["calls"], 6)

    def test_tracer_does_not_measure_itself(self):
        """Bookkeeping frames must never appear as workload hotspots."""
        _, report = self._run(lambda: sum(range(50_000)))
        names = {h["qualified_name"].rsplit(".", 1)[-1] for h in report["hotspots"]}
        for internal in ("_stop_sampler", "_on_return", "_local_trace",
                         "_global_trace", "_report", "_pump"):
            self.assertNotIn(internal, names)

    def test_self_time_excludes_children(self):
        def leaf():
            return sum(range(50_000))

        def parent():
            return leaf() + leaf()

        _, report = self._run(parent)
        by_name = self._by_name(report)
        p, l = by_name["parent"], by_name["leaf"]
        self.assertEqual(l["calls"], 2)
        self.assertGreaterEqual(p["self_ms"], 0.0)
        # parent spends nearly all its time inside leaf, so self time is small.
        self.assertLessEqual(p["self_ms"], p["total_ms"] + 1e-6)
        self.assertLessEqual(l["self_ms"], l["total_ms"] + 1e-6)

    def test_hardware_measurement_is_reported(self):
        _, report = self._run(lambda: sum(range(10_000)), meter=_FakeMeter(0.5))
        self.assertTrue(report["measurement_is_hardware"])
        self.assertEqual(report["measurement_method"], "rapl")

    def test_modelled_backend_is_not_claimed_as_hardware(self):
        meter = _FakeMeter()
        meter.backend = "model"
        _, report = self._run(lambda: sum(range(10_000)), meter=meter)
        self.assertFalse(report["measurement_is_hardware"])
        self.assertEqual(report["ranked_by"], "self_time")

    def test_tracer_is_restored_after_run(self):
        import sys

        before = sys.gettrace()
        self._run(lambda: sum(range(1000)))
        self.assertEqual(sys.gettrace(), before)

    def test_no_meter_does_not_crash(self):
        _, report = self._run(lambda: sum(range(1000)), meter=None)
        self.assertIn("measurement_method", report)

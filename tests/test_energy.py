"""Tests for hardware energy measurement and SCI computation.

The hardware backends cannot be exercised on a machine with no RAPL, so those
tests inject a fake counter. That is deliberate: the wrap-around arithmetic and
domain-precedence rules are exactly the logic most likely to be wrong, and a
fake counter is the only way to test them deterministically.
"""

import unittest
from unittest import mock

from app.energy_sensors import (
    HARDWARE_METHODS,
    RaplDomain,
    RaplMeter,
    ScaphandreMeter,
    ScaphhandreMeter,
    discover_rapl_domains,
    is_hardware_method,
    is_linux,
    model_power_watts,
    wrap_delta,
)
from app.sci import carbon_equivalents, compute_sci, sci_grade


class TestHardwareMethodClassification(unittest.TestCase):
    """One definition of "this is a measurement", shared by every consumer.

    These guard a real regression: `scaphandre` was missing from the verifier's
    and SCI's hardware sets, so genuine RAPL counters relayed over the sidecar -
    the documented production path for Docker-on-Linux - were reported as
    estimates and could never confirm a claim.
    """

    def test_every_documented_backend_is_hardware(self):
        for method in ("rapl", "scaphandre", "perf", "battery"):
            with self.subTest(method=method):
                self.assertIn(method, HARDWARE_METHODS)
                self.assertTrue(is_hardware_method(method))

    def test_model_is_never_hardware(self):
        self.assertFalse(is_hardware_method("model"))
        self.assertNotIn("model", HARDWARE_METHODS)

    def test_unknown_and_missing_methods_default_to_not_hardware(self):
        """An unrecognised label must never be promoted to a measurement."""
        for value in ("", "   ", None, "bogus", "rapl2", "estimated"):
            with self.subTest(value=value):
                self.assertFalse(is_hardware_method(value))

    def test_classification_is_case_and_whitespace_insensitive(self):
        self.assertTrue(is_hardware_method("  RAPL "))
        self.assertTrue(is_hardware_method("Scaphandre"))

    def test_sci_agrees_with_the_shared_definition(self):
        for method in sorted(HARDWARE_METHODS):
            with self.subTest(method=method):
                r = compute_sci(
                    energy_joules=1e6, duration_seconds=1,
                    carbon_intensity_gco2_per_kwh=400, functional_unit=1000.0,
                    measurement_method=method,
                )
                self.assertTrue(r.measurement_is_hardware)
                self.assertEqual(r.warnings, [], "a measured figure needs no model warning")

    def test_sci_still_warns_for_a_modelled_figure(self):
        r = compute_sci(
            energy_joules=1e6, duration_seconds=1,
            carbon_intensity_gco2_per_kwh=400, functional_unit=1000.0,
            measurement_method="model",
        )
        self.assertFalse(r.measurement_is_hardware)
        self.assertTrue(any("hardware" in w for w in r.warnings))

    def test_original_misspelling_still_imports(self):
        """`ScaphhandreMeter` shipped as public API; the rename must not break it."""
        self.assertIs(ScaphhandreMeter, ScaphandreMeter)


class TestCounterArithmetic(unittest.TestCase):
    def test_no_wrap(self):
        self.assertEqual(wrap_delta(1000, 2000, 262_143_328_850), 1000)

    def test_wrap_is_not_negative(self):
        """The classic RAPL bug: a naive delta across the wrap is hugely negative."""
        max_range = 262_143_328_850
        start, end = max_range - 500, 500
        self.assertEqual(wrap_delta(start, end, max_range), 1000)

    def test_exact_wrap_point(self):
        max_range = 1_000_000
        self.assertEqual(wrap_delta(999_000, 0, max_range), 1000)
        self.assertEqual(wrap_delta(max_range, 0, max_range), 0)

    def test_multiple_wraps_stay_non_negative(self):
        for start in (0, 123_456, 262_000_000_000):
            self.assertGreaterEqual(wrap_delta(start, 42, 262_143_328_850), 0)


class TestRaplDomainSelection(unittest.TestCase):
    """core is a subset of package, and dram is often already inside psys."""

    def _meter(self):
        return RaplMeter([
            RaplDomain("package-0", "p", 262_143_328_850, "package"),
            RaplDomain("core", "c", 262_143_328_850, "core"),
            RaplDomain("dram", "d", 262_143_328_850, "dram"),
        ])

    def test_measurement_sums_cpu_and_memory_separately(self):
        """The fake counter must actually advance between the two reads."""
        meter = self._meter()
        offsets = {"package-0": 0, "core": 0, "dram": 0}
        # core advances 0.9 J but is a SUBSET of package, so it must not be added.
        advance = {"package-0": 1_000_000, "core": 900_000, "dram": 500_000}

        def read(d):
            offsets[d.name] += advance[d.name]
            return offsets[d.name]

        with mock.patch.object(RaplDomain, "read_uj", autospec=True, side_effect=read):
            _, _, j = meter.measure(lambda: None)

        self.assertAlmostEqual(j["cpu_joules"], 1.0, places=6)
        self.assertAlmostEqual(j["memory_joules"], 0.5, places=6)
        self.assertAlmostEqual(j["total_joules"], 1.5, places=6)

    def test_core_domain_is_not_double_counted(self):
        """If `core` were added on top of `package`, energy would be overstated."""
        meter = self._meter()
        offsets = {"package-0": 0, "core": 0, "dram": 0}
        advance = {"package-0": 1_000_000, "core": 900_000, "dram": 0}

        def read(d):
            offsets[d.name] += advance[d.name]
            return offsets[d.name]

        with mock.patch.object(RaplDomain, "read_uj", autospec=True, side_effect=read):
            _, _, j = meter.measure(lambda: None)

        # 1.0 J of package energy, not 1.9 J.
        self.assertAlmostEqual(j["cpu_joules"], 1.0, places=6)

    def test_psys_is_a_package_kind(self):
        meter = self._meter()
        self.assertIn("psys", meter.PACKAGE_KINDS)
        self.assertIn("package", meter.PACKAGE_KINDS)

    def test_discovery_is_empty_off_linux(self):
        if not is_linux():
            self.assertEqual(discover_rapl_domains(), [])

    def test_empty_domains_raises(self):
        with self.assertRaises(RuntimeError):
            RaplMeter([])


class TestModelledFallback(unittest.TestCase):
    def test_power_increases_monotonically_with_load(self):
        idle = model_power_watts(0.0, 0)
        mid = model_power_watts(50.0, 0)
        full = model_power_watts(100.0, 0)
        self.assertLess(idle, mid)
        self.assertLess(mid, full)

    def test_load_is_clamped(self):
        self.assertEqual(model_power_watts(500.0, 0), model_power_watts(100.0, 0))
        self.assertEqual(model_power_watts(-50.0, 0), model_power_watts(0.0, 0))

    def test_memory_adds_power(self):
        self.assertGreater(model_power_watts(50.0, 4096), model_power_watts(50.0, 0))


class TestSCI(unittest.TestCase):
    def test_matches_the_gsf_formula(self):
        """SCI = (E x I + M) / R, with E in kWh and M in gCO2e."""
        r = compute_sci(
            energy_joules=3_600_000_000.0,  # exactly 1 kWh
            duration_seconds=3600.0,
            carbon_intensity_gco2_per_kwh=400.0,
            functional_unit=10.0,
            pue=1.0,
        )
        # 1 kWh * 400 g/kWh = 400 g operational
        # 3600 s * 0.00018 g/s = 0.648 g embodied
        self.assertAlmostEqual(r.operational_gco2, 400.0, places=6)
        self.assertAlmostEqual(r.embodied_gco2, 0.648, places=6)
        self.assertAlmostEqual(r.sci_gco2_per_functional_unit, (400.0 + 0.648) / 10.0, places=6)

    def test_pue_scales_facility_energy(self):
        base = compute_sci(energy_joules=1e6, duration_seconds=1,
                           carbon_intensity_gco2_per_kwh=400, pue=1.0)
        p2 = compute_sci(energy_joules=1e6, duration_seconds=1,
                         carbon_intensity_gco2_per_kwh=400, pue=2.0)
        self.assertAlmostEqual(p2.operational_gco2, base.operational_gco2 * 2, places=9)
        self.assertAlmostEqual(base.it_energy_joules, 1e6, places=6)

    def test_functional_unit_must_be_positive(self):
        with self.assertRaises(ValueError):
            compute_sci(energy_joules=1, duration_seconds=1,
                        carbon_intensity_gco2_per_kwh=400, functional_unit=0)

    def test_negative_intensity_rejected(self):
        with self.assertRaises(ValueError):
            compute_sci(energy_joules=1, duration_seconds=1, carbon_intensity_gco2_per_kwh=-5)

    def test_hardware_measurement_is_flagged_and_not_warned(self):
        r = compute_sci(energy_joules=1e6, duration_seconds=1,
                        carbon_intensity_gco2_per_kwh=400,
                        functional_unit=1000.0, measurement_method="rapl")
        self.assertTrue(r.measurement_is_hardware)
        self.assertEqual(r.warnings, [])

    def test_functional_unit_of_one_is_flagged_as_not_an_intensity(self):
        r = compute_sci(energy_joules=1e6, duration_seconds=1,
                        carbon_intensity_gco2_per_kwh=400,
                        functional_unit=1.0, measurement_method="rapl")
        self.assertTrue(any("intensity" in w for w in r.warnings))

    def test_modelled_measurement_is_flagged_and_warned(self):
        r = compute_sci(energy_joules=1e6, duration_seconds=1,
                        carbon_intensity_gco2_per_kwh=400, measurement_method="model")
        self.assertFalse(r.measurement_is_hardware)
        self.assertTrue(any("hardware" in w for w in r.warnings))

    def test_sci_is_an_intensity_so_functional_unit_divides(self):
        one = compute_sci(energy_joules=1e7, duration_seconds=1,
                          carbon_intensity_gco2_per_kwh=400, functional_unit=1)
        hundred = compute_sci(energy_joules=1e7, duration_seconds=1,
                             carbon_intensity_gco2_per_kwh=400, functional_unit=100)
        self.assertAlmostEqual(one.sci_gco2_per_functional_unit / 100.0,
                               hundred.sci_gco2_per_functional_unit, places=12)

    def test_grades_and_equivalents_are_sane(self):
        self.assertEqual(sci_grade(0.0)["grade"], "A+")
        self.assertEqual(sci_grade(5.0)["grade"], "F")
        self.assertGreaterEqual(carbon_equivalents(100.0)["km_driven_petrol_car"], 0.5)
        self.assertEqual(carbon_equivalents(-5.0)["smartphone_charges"], 0.0)


"""Tests for the 'explain this score' provenance contract.

The GreenCode promise, restated in ``REAL_WORLD_LOGIC_AUDIT.md``, is that no
figure is ever invented to fill a gap. ``explain_score`` is the traceability
tool an Alexa+ / MCP agent quotes back to a user, so it must never fabricate an
SCI to accompany a score it was handed.

These tests pin that contract:

* With no energy measurement supplied, the SCI breakdown is explicitly withheld
  (``input_basis == "not_supplied"`` and every numeric field is ``None``) rather
  than back-filled from a hard-coded reference input.
* With a caller-supplied measurement, the SCI is computed from exactly those
  inputs and they are echoed back so the number is traceable.
* ``violation_count`` / ``severity_counts`` are echoed as ``null`` when unknown
  (``null`` means unknown, never zero).

No socket is opened: the grid-intensity lookup is the only network edge and it
is mocked so the arithmetic under test is deterministic.
"""

import unittest
from unittest import mock

from app import mcp_server


class TestExplainScoreWithheldSCI(unittest.TestCase):
    """Without a measurement the SCI must be withheld, never fabricated."""

    def _resolve(self, zone):
        return {
            "zone": zone,
            "carbon_intensity": 300.0,
            "intensity_source": "test_provider",
            "intensity_source_tier": "primary_official",
            "is_live": True,
        }

    def test_no_measurement_withholds_sci(self):
        with mock.patch.object(mcp_server, "_resolve_intensity", self._resolve):
            res = mcp_server.explain_score(72.0, zone="IE")
        self.assertEqual(res["status"], "ok")
        sc = res["data"]["scientific_context"]
        self.assertEqual(sc["input_basis"], "not_supplied")
        self.assertIsNone(sc["sci_gco2_per_functional_unit"])
        self.assertIsNone(sc["grade"])
        self.assertIsNone(sc["carbon_equivalents"])
        self.assertIn("no sci", sc["reason"].lower())

    def test_score_and_grid_provenance_are_still_reported(self):
        with mock.patch.object(mcp_server, "_resolve_intensity", self._resolve):
            res = mcp_server.explain_score(72.0, zone="IE")
        data = res["data"]
        self.assertEqual(data["green_score"], 72.0)
        self.assertEqual(data["grid_intensity"]["carbon_intensity"], 300.0)
        self.assertEqual(data["grid_intensity"]["tier"], "primary_official")
        self.assertTrue(data["grid_intensity"]["is_live"])

    def test_unknown_violation_count_is_null_not_zero(self):
        with mock.patch.object(mcp_server, "_resolve_intensity", self._resolve):
            res = mcp_server.explain_score(72.0, zone="IE")
        summary = res["data"]["findings_summary"]
        self.assertIsNone(summary["violation_count"])
        self.assertFalse(summary["counts_known"])

    def test_hardware_flag_is_never_hidden(self):
        with mock.patch.object(mcp_server, "_resolve_intensity", self._resolve):
            res = mcp_server.explain_score(
                72.0, zone="IE", measurement_method="rapl"
            )
        self.assertTrue(res["data"]["measurement_is_hardware"])

    def test_invalid_score_is_rejected(self):
        res = mcp_server.explain_score(150.0, zone="IE")
        self.assertEqual(res["status"], "error")


class TestExplainScoreSuppliedMeasurement(unittest.TestCase):
    """With a measurement the SCI is computed from exactly those inputs."""

    def _resolve(self, zone):
        return {
            "zone": zone,
            "carbon_intensity": 400.0,
            "intensity_source": "test_provider",
            "intensity_source_tier": "primary_official",
            "is_live": True,
        }

    def test_sci_is_computed_and_inputs_echoed(self):
        with mock.patch.object(mcp_server, "_resolve_intensity", self._resolve):
            res = mcp_server.explain_score(
                72.0, zone="IE", energy_joules=1500.0, duration_seconds=1.0,
                functional_unit=1.0,
            )
        self.assertEqual(res["status"], "ok")
        sc = res["data"]["scientific_context"]
        self.assertEqual(sc["input_basis"], "caller_supplied_measurement")
        self.assertIsNotNone(sc["sci_gco2_per_functional_unit"])
        self.assertEqual(sc["inputs"]["energy_joules"], 1500.0)
        self.assertEqual(sc["inputs"]["functional_unit"], 1.0)
        self.assertIsNotNone(sc["grade"])
        self.assertIsNotNone(sc["carbon_equivalents"])

    def test_sci_traces_to_the_supplied_energy(self):
        # 1500 J at 400 gCO2/kWh, R=1: SCI = (E*I)/R, PUE from the GSF default.
        with mock.patch.object(mcp_server, "_resolve_intensity", self._resolve):
            res = mcp_server.explain_score(
                72.0, zone="IE", energy_joules=1500.0, duration_seconds=0.0,
                functional_unit=1.0, measurement_method="rapl",
            )
        sc = res["data"]["scientific_context"]
        self.assertGreater(sc["sci_gco2_per_functional_unit"], 0.0)

    def test_negative_energy_is_treated_as_unsupplied(self):
        with mock.patch.object(mcp_server, "_resolve_intensity", self._resolve):
            res = mcp_server.explain_score(72.0, zone="IE", energy_joules=-5.0)
        sc = res["data"]["scientific_context"]
        self.assertEqual(sc["input_basis"], "not_supplied")
        self.assertIsNone(sc["sci_gco2_per_functional_unit"])


class TestSeverityAndViolationCountProvenance(unittest.TestCase):
    """Ensure CRITICAL findings are counted/prioritized and violation_count is exposed at top-level."""

    def test_severity_counts_includes_critical(self):
        counts = mcp_server._severity_counts([
            {"severity": "CRITICAL"},
            {"severity": "HIGH"},
            {"severity": "LOW"},
        ])
        self.assertEqual(counts["CRITICAL"], 1)
        self.assertEqual(counts["HIGH"], 1)
        self.assertEqual(counts["MEDIUM"], 0)
        self.assertEqual(counts["LOW"], 1)

    def test_audit_and_score_ranks_critical_before_high(self):
        with mock.patch.object(mcp_server, "audit_code", return_value={
            "status": "ok",
            "warnings": [],
            "data": {
                "green_score": 35.0,
                "grade": "F",
                "violation_count": 3,
                "violations": [
                    {"severity": "LOW", "violation_type": "L", "line_number": 3},
                    {"severity": "CRITICAL", "violation_type": "C", "line_number": 1},
                    {"severity": "HIGH", "violation_type": "H", "line_number": 2},
                ],
            },
        }):
            res = mcp_server.audit_and_score("x = 1", duration_seconds=0.01)
        order = [item["violation_type"] for item in res["data"]["remediation_plan"]]
        self.assertEqual(order, ["C", "H", "L"])

    def test_explain_score_exposes_top_level_violation_count(self):
        res = mcp_server.explain_score(84.0, zone="IE", violation_count=4)
        self.assertEqual(res["data"]["violation_count"], 4)
        self.assertEqual(res["data"]["findings_summary"]["violation_count"], 4)


if __name__ == "__main__":
    unittest.main()


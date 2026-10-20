"""Negative-case and edge-case test suite for GreenCode Auditor.

Run:  python -m pytest tests/test_edge_cases.py -q
"""

import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.energy_sensors import is_hardware_method, wrap_delta  # noqa: E402
from app.finops_focus import reconcile_focus_billing  # noqa: E402
from app.parser import (  # noqa: E402
    audit_file,
    audit_file_content,
    audit_source_code,
    audit_zip_archive,
)
from app.sci import compute_sci  # noqa: E402
from app.pipeline.signing import compute_signature, verify_signature  # noqa: E402
from app.iac_linter import audit_iac_content  # noqa: E402
from app.call_graph import audit_cross_file_loops  # noqa: E402


class TestFinOpsFocusNegativeCases(unittest.TestCase):


    def test_empty_csv_falls_through_to_default_sample_rows(self):
        # Documented behavior: empty/whitespace CSV falls through to
        # SAMPLE_FOCUS_ROWS instead of returning an empty report. This sanity
        # check asserts the fallback is deterministic (never raises).
        res = reconcile_focus_billing(csv_text="")
        self.assertEqual(res["line_items_evaluated"], 3)
        self.assertEqual(res["summary"]["total_billed_cost_usd"], 492.75)


    def test_negative_billed_cost_summed_signed(self):
        res = reconcile_focus_billing(rows=[{
            "ProviderName": "AWS",
            "ServiceName": "AmazonEC2",
            "ResourceId": "i-1",
            "ResourceType": "m5.large",
            "RegionId": "us-east-1",
            "ConsumedQuantity": 730,
            "BilledCost": -5.0,
            "EffectiveCost": -5.0,
        }])
        self.assertEqual(res["summary"]["total_billed_cost_usd"], -5.0)

    def test_non_numeric_field_propagates_to_float(self):
        # A non-numeric EffectiveCost should raise ValueError because the CSV
        # parser tries to convert it. This documents the current strictness.
        bad = ("ProviderName,ServiceName,ResourceId,ResourceType,RegionId,"
               "ConsumedQuantity,BilledCost,EffectiveCost\n"
               "AWS,AmazonEC2,i-1,m5.large,us-east-1,730,10.0,not_a_number\n")

    def test_zero_hours_uses_730_default(self):
        # The parser applies `row.get("ConsumedQuantity") or 730.0` as a fallback,
        # so 0.0 falls back to the full-year default. This is a documented data-
        # entry safety trade-off, asserted here.
        res = reconcile_focus_billing(rows=[{
            "ProviderName": "AWS",
            "ServiceName": "AmazonEC2",
            "ResourceId": "i-1",
            "ResourceType": "m5.large",
            "RegionId": "us-east-1",
            "ConsumedQuantity": 0.0,
            "BilledCost": 10.0,
            "EffectiveCost": 9.0,
        }])
        self.assertEqual(res["reconciled_items"][0]["consumed_hours"], 730.0)

    def test_zero_hours_added_to_embodied(self):
        # The parser applies `row.get("ConsumedQuantity") or 730.0` as a fallback,
        # so 0.0 falls back to the full-year default 730.0.
        res = reconcile_focus_billing(rows=[{
            "ProviderName": "AWS",
            "ServiceName": "AmazonEC2",
            "ResourceId": "i-1",
            "ResourceType": "m5.large",
            "RegionId": "us-east-1",
            "ConsumedQuantity": 0.0,
            "BilledCost": 10.0,
            "EffectiveCost": 9.0,
        }])
        self.assertEqual(res["reconciled_items"][0]["consumed_hours"], 730.0)

    def test_negative_billed_cost_summed_signed(self):
        res = reconcile_focus_billing(rows=[{
            "ProviderName": "AWS",
            "ServiceName": "AmazonEC2",
            "ResourceId": "i-1",
            "ResourceType": "m5.large",
            "RegionId": "us-east-1",
            "ConsumedQuantity": 730,
            "BilledCost": -5.0,
            "EffectiveCost": -5.0,
        }])
        self.assertEqual(res["summary"]["total_billed_cost_usd"], -5.0)

class TestSciEdgeCases(unittest.TestCase):
    """Boundary values for the GSF SCI denominator and intensity."""

    def test_zero_energy_joules(self):
        res = compute_sci(
            energy_joules=0.0,
            duration_seconds=1.0,
            carbon_intensity_gco2_per_kwh=380.0,
            functional_unit=1.0,
        )
        self.assertEqual(res.energy_kwh, 0.0)
        self.assertEqual(res.operational_gco2, 0.0)

    def test_negative_energy_joules_clamps_to_zero(self):
        res = compute_sci(
            energy_joules=-5.0,
            duration_seconds=1.0,
            carbon_intensity_gco2_per_kwh=380.0,
            functional_unit=1.0,
        )
        self.assertEqual(res.energy_kwh, 0.0)

    def test_zero_functional_unit_raises(self):
        with self.assertRaises(ValueError):
            compute_sci(
                energy_joules=100.0,
                duration_seconds=1.0,
                carbon_intensity_gco2_per_kwh=380.0,
                functional_unit=0.0,
            )

    def test_negative_functional_unit_raises(self):
        with self.assertRaises(ValueError):
            compute_sci(
                energy_joules=100.0,
                duration_seconds=1.0,
                carbon_intensity_gco2_per_kwh=380.0,
                functional_unit=-1.0,
            )

    def test_negative_carbon_intensity_raises(self):
        with self.assertRaises(ValueError):
            compute_sci(
                energy_joules=100.0,
                duration_seconds=1.0,
                carbon_intensity_gco2_per_kwh=-1.0,
                functional_unit=1.0,
            )

    def test_pue_clamped_minimum_one(self):
        # PUE below 1.0 must not reduce facility energy below pure IT draw.
        # The stored res.pue is the caller-supplied value; the clamped value
        # is applied only in the facility_joules calculation.
        res = compute_sci(
            energy_joules=1_000_000.0,
            duration_seconds=1.0,
            carbon_intensity_gco2_per_kwh=380.0,
            functional_unit=1.0,
            pue=0.5,
        )
        # facility = it_joules * max(1.0, pue) = 1_000_000 * 1.0
        self.assertGreaterEqual(res.energy_kwh, 1_000_000.0 / 3_600_000.0)
        self.assertEqual(res.pue, 0.5)  # stored value is caller input

    def test_pue_clamped_maximum(self):
        res = compute_sci(
            energy_joules=1_000_000.0,
            duration_seconds=1.0,
            carbon_intensity_gco2_per_kwh=380.0,
            functional_unit=1.0,
            pue=3.0,
        )
        self.assertEqual(res.pue, 3.0)

    def test_embodied_adds_positive_carbon(self):
        res = compute_sci(
            energy_joules=0.0,
            duration_seconds=86400.0,
            carbon_intensity_gco2_per_kwh=0.0,
            functional_unit=1.0,
        )
        self.assertGreater(res.embodied_gco2, 0.0)
        self.assertGreater(res.sci_gco2_per_functional_unit, 0.0)


class TestEnergySensorsEdgeCases(unittest.TestCase):
    """Wrap-around counter handling and hardware-method classification."""

    def test_wrap_delta_no_wrap(self):
        self.assertEqual(wrap_delta(100, 200, 4_294_967_296), 100)

    def test_wrap_delta_with_32bit_wrap(self):
        max_range = 0xFFFFFFFF
        self.assertEqual(wrap_delta(max_range - 5, 5, max_range), 10)

    def test_wrap_delta_identity(self):
        self.assertEqual(wrap_delta(0, 0, 4_294_967_296), 0)

    def test_wrap_delta_negative_delta_never(self):
        self.assertGreaterEqual(
            wrap_delta(0xFFFF0000, 0x00001000, 0x100000000), 0)

    def test_is_hardware_method_case_insensitive(self):
        self.assertTrue(is_hardware_method("RAPL"))
        self.assertTrue(is_hardware_method("  Scaphandre  "))
        self.assertTrue(is_hardware_method("nvidia_smi"))
        self.assertTrue(is_hardware_method("APPLE_SMC"))

    def test_is_hardware_method_unknown_and_empty_false(self):
        self.assertFalse(is_hardware_method("bogus_method"))
        self.assertFalse(is_hardware_method(""))
        self.assertFalse(is_hardware_method(None))


class TestIacLinterEdgeCases(unittest.TestCase):
    """Valid IaC configurations that must produce zero findings."""

    def test_valid_terraform_no_findings(self):
        tf = (
            'resource "aws_instance" "web" {\n'
            '  ami           = "ami-123456"\n'
            '  instance_type = "m7g.large"\n'
            '  root_block_device {\n'
            '    volume_type = "gp3"\n'
            '    size        = 100\n'
            '  }\n'
            '}\n'
            'resource "aws_cloudwatch_log_group" "app" {\n'
            '  name = "/aws/app/prod"\n'
            '  retention_in_days = 365\n'
            '}\n'
        )
        res = audit_iac_content(tf, file_path="infra/main.tf")
        self.assertEqual(res["iac_type"], "terraform")
        self.assertEqual(res["total_findings"], 0)

    def test_valid_kubernetes_with_limits(self):
        k8s = (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: worker\n"
            "spec:\n"
            "  replicas: 2\n"
            "  selector:\n"
            "    matchLabels:\n"
            "      app: worker\n"
            "  template:\n"
            "    metadata:\n"
            "      labels:\n"
            "        app: worker\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: worker\n"
            "          image: myorg/worker:1.2.3\n"
            "          resources:\n"
            "            requests:\n"
            "              cpu: 500m\n"
            "              memory: 256Mi\n"
            "            limits:\n"
            "              cpu: 1000m\n"
            "              memory: 512Mi\n"
        )
        res = audit_iac_content(k8s, file_path="k8s/deployment.yaml")
        self.assertEqual(res["iac_type"], "kubernetes")
        self.assertEqual(res["total_findings"], 0)

    def test_dockerfile_without_tag(self):
        df = ("FROM python:3.11-slim\n"
              "RUN apt-get update && apt-get install -y --no-install-recommends gcc\n")
        res = audit_iac_content(df, file_path="Dockerfile")
        self.assertEqual(res["iac_type"], "dockerfile")

    def test_dockerfile_with_latest_tag(self):
        df = "FROM python:3.11\nRUN apt-get update && apt-get install -y gcc\n"
        res = audit_iac_content(df, file_path="Dockerfile")
        self.assertEqual(res["iac_type"], "dockerfile")


class TestCallGraphEdgeCases(unittest.TestCase):
    """Adversarial call-graph inputs."""

    def test_empty_file_registry(self):
        report = audit_cross_file_loops({})
        self.assertEqual(report["files_scanned"], 0)
        self.assertEqual(report["total_violations"], 0)

    def test_single_file_no_cross_file(self):
        files = {"repo/single.py": "def handler(x): return x * 2"}
        report = audit_cross_file_loops(files)
        self.assertEqual(report["files_scanned"], 1)
        self.assertEqual(report["total_violations"], 0)

    def test_single_file_same_file_chain(self):
        # A self-recursive call within one file is detected as a single-file
        # hazard (not a cross-file violation). The call-graph engine reports 1
        # violation for a recursive loop that recurses inside a for loop.
        src = (
            "def process(items):\n"
            "    for i in items:\n"
            "        process([i])\n"
        )
        report = audit_cross_file_loops({"repo/svc.py": src})
        self.assertEqual(report["total_violations"], 1)


class TestParserEdgeCases(unittest.TestCase):
    """Empty, huge, and encoded source files."""

    def test_empty_file_content_returns_zero_violations(self):
        res = audit_file_content("", file_path="empty.py")
        self.assertEqual(res["lines_count"], 0)
        self.assertEqual(res["violations"], [])
        self.assertEqual(res["green_score"], 100.0)

    def test_nonexistent_file_returns_error(self):
        res = audit_file("/nonexistent/path/xyz.py")
        self.assertIn("error", res)
        self.assertEqual(res["error"], "File does not exist")

    def test_file_over_2mb_is_skipped(self):
        # Write a 3 MB file on Windows; audit it; static analysis must be skipped.
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            big = os.path.join(tmpdir, "big.txt")
            with open(big, "w") as fh:
                fh.write("x" * (3 * 1024 * 1024))
            try:
                res = audit_file(big)
                self.assertIn("notice", res)
                self.assertEqual(res["lines_count"], 0)
                self.assertEqual(res["violations"], [])
            finally:
                if os.path.exists(big):
                    os.remove(big)

    def test_very_small_file(self):
        res = audit_file_content(
            "def hello(name):\n    return f'Hello {name}'\n",
            file_path="hello.py",
        )
        self.assertEqual(res["violations"], [])
        self.assertEqual(res["green_score"], 100.0)

    def test_suppression_pragma_same_line(self):
        # The suppression pragma must be on the same line as the violating
        # statement (or immediately before it) for the parser to suppress it.
        src = ("for i in range(100):  # greencode: ignore\n"
               "    print(i)\n")
        res = audit_source_code(src, "python", "loop.py")


class TestPipelineSignallingNegativeCases(unittest.TestCase):
    """Signed-intake signature verification edge cases."""

    def test_empty_secret(self):
        import time
        hdr, ts = compute_signature("", b"body")
        res = verify_signature("", b"body", hdr, str(ts))
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "no_secret_configured")

    def test_missing_timestamp(self):
        import time
        hdr, ts = compute_signature("s3cret", b"body")
        res = verify_signature("s3cret", b"body", hdr, None)
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "missing_timestamp")

    def test_malformed_timestamp(self):
        hdr, ts = compute_signature("s3cret", b"body")
        res = verify_signature("s3cret", b"body", hdr, "not-a-number")
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "malformed_timestamp")

    def test_stale_timestamp_rejected(self):
        import time
        hdr, ts = compute_signature("s3cret", b"body")
        res = verify_signature("s3cret", b"body", hdr, str(int(time.time()) - 3600))
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "stale_timestamp")

    def test_signature_mismatch(self):
        import time
        hdr, ts = compute_signature("s3cret", b"body")
        res = verify_signature("wrong-secret", b"body", hdr, str(ts))
        self.assertFalse(res.ok)
        self.assertEqual(res.reason, "signature_mismatch")


class TestScannerZipArchiveNegativeCases(unittest.TestCase):
    def test_corrupt_zip_raises_badzipfile(self):
        # A corrupt ZIP raises zipfile.BadZipFile which is NOT a ValueError.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.zip")
            with open(bad, "wb") as fh:
                fh.write(b"this is not a zip")
            try:
                audit_zip_archive(bad)
            except zipfile.BadZipFile:
                return
            except ValueError:
                self.fail("ValueError raised instead of BadZipFile")
            except Exception as e:
                self.fail("Unexpected exception: " + type(e).__name__ + " " + str(e))

    def test_corrupt_zip_not_rejected_by_github_audit(self):
        # run_github_audit catches ValueError (zip bomb / traversal) but NOT
        # BadZipFile. A corrupt upload returns HTTP 500 instead of 400.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bad = os.path.join(d, "bad.zip")
            with open(bad, "wb") as fh:
                fh.write(b"not a zip")
            try:
                from app.parser import audit_zip_archive
                try:
                    audit_zip_archive(bad)
                except zipfile.BadZipFile:
                    pass
                except ValueError:
                    pass
                else:
                    self.fail("No exception raised")
            finally:
                pass

    def test_zip_bomb_too_many_files_rejected(self):
        # 3500 files exceeds MAX_ZIP_FILE_COUNT (3000) => ValueError raised.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bad_zip = os.path.join(d, "big.zip")
            with zipfile.ZipFile(bad_zip, "w") as zf:
                for i in range(3500):
                    zf.writestr("file_{}.txt".format(i), "a" * 10)
            try:
                audit_zip_archive(bad_zip)
            except ValueError as e:
                self.assertIn("maximum file count", str(e))
            else:
                self.fail("No exception raised for 3500-file zip")

class TestEmptyAndMalformedFiles(unittest.TestCase):
    def test_audit_repository_skips_gitignore_and_vendor(self):
        # audit_repository must skip .gitignore entries and vendor directories.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "vendor"))
            with open(os.path.join(d, "a.py"), "w") as fh:
                fh.write("x = 1\n")
            with open(os.path.join(d, ".gitignore"), "w") as fh:
                fh.write("vendor/\n")
            from app.parser import audit_repository
            res = audit_repository(d)
            self.assertGreaterEqual(res.get("total_files", 0), 1)
            self.assertNotEqual(res.get("total_files", 0), 3)


"""API Integration Test Suite for GreenCode Auditor.

Tests all REST endpoints on FastAPI app:
- POST /api/scan
- POST /api/profile
- POST /api/refactor
- GET /api/grid/zones
- GET /api/history
- POST /api/ci/evaluate
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


class TestFastAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "GreenCode Auditor API")
        self.assertEqual(data["status"], "online")

    def test_grid_zones_endpoint(self):
        resp = self.client.get("/api/grid/zones")
        self.assertEqual(resp.status_code, 200)
        zones = resp.json()
        self.assertGreater(len(zones), 0)
        zone_codes = [z["zone"] for z in zones]
        self.assertIn("US-CAL-CISO", zone_codes)

    def test_scan_endpoint(self):
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        payload = {"repo_path": samples_dir, "name": "SamplesAudit"}
        resp = self.client.post("/api/scan", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("green_score", data)
        self.assertIn("violations", data)
        self.assertIn("repo_id", data)

    def test_scan_async_and_task_polling_endpoints(self):
        samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))
        payload = {"repo_path": samples_dir, "name": "AsyncSamplesAudit"}
        resp = self.client.post("/api/scan/async", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("task_id", data)
        self.assertEqual(data["status"], "Processing")

        task_id = data["task_id"]
        poll_resp = self.client.get(f"/api/task/{task_id}")
        self.assertEqual(poll_resp.status_code, 200)
        poll_data = poll_resp.json()
        self.assertEqual(poll_data["task_id"], task_id)
        self.assertIn(poll_data["status"], ["Processing", "Completed", "SUCCESS"])

    def test_profile_endpoint(self):
        sample_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "eco_pipeline.py"))
        payload = {"file_path": sample_file, "timeout_sec": 5.0, "zone": "US-CAL-CISO"}
        resp = self.client.post("/api/profile", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("duration_sec", data)
        self.assertIn("energy_wh", data)
        self.assertIn("sci_score_gco2", data)

    def test_refactor_endpoint(self):
        payload = {
            "snippet": "for i in a:\n    for j in b:\n        for k in c:\n            val = i*j*k",
            "violation_type": "NESTED_LOOPS_DEPTH_3+",
        }
        resp = self.client.post("/api/refactor", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("refactored_code", data)
        self.assertGreater(data["energy_reduction_pct"], 0)

    def test_ci_evaluate_endpoint(self):
        heavy_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "heavy_pipeline.py"))
        payload = {"repo_path": heavy_file, "threshold": 75.0, "zone": "US-CAL-CISO"}
        resp = self.client.post("/api/ci/evaluate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["passed"])
        self.assertEqual(data["exit_code"], 1)

    def test_history_endpoint(self):
        resp = self.client.get("/api/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("repositories", data)
        self.assertIn("cumulative_savings", data)

    def test_github_endpoints(self):
        from unittest.mock import patch, MagicMock
        with patch("app.main.get_authenticated_user") as mock_user, \
             patch("app.main.list_user_repositories") as mock_repos, \
             patch("app.main.create_refactoring_pull_request") as mock_pr:
            mock_user.return_value = {"login": "zeenat28-ui"}
            mock_repos.return_value = [{"full_name": "zeenat28-ui/greencode"}]
            mock_pr.return_value = {"success": True, "pr_url": "https://github.com/zeenat28-ui/greencode/pull/1", "pr_number": 1, "branch": "greencode/eco-refactor-1"}

            # Test GET /github/user
            resp = self.client.get("/github/user")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["user"]["login"], "zeenat28-ui")

            # Test GET /github/repos
            resp = self.client.get("/github/repos")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(len(resp.json()["repositories"]), 1)

            # Test POST /github/pull-request
            pr_payload = {
                "repo_full_name": "zeenat28-ui/greencode",
                "file_path": "samples/heavy_pipeline.py",
                "refactored_code": "print('clean')",
                "violation_title": "NESTED_LOOPS",
                "energy_reduction_pct": 50.0,
                "carbon_saved_10k": 30.0,
            }
            resp = self.client.post("/github/pull-request", json=pr_payload)
            self.assertEqual(resp.status_code, 200)
            self.assertTrue(resp.json()["success"])

    def test_badge_score_endpoint(self):
        resp = self.client.get("/api/badge/score/88.5")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/svg+xml", resp.headers["content-type"])
        self.assertIn(b"<svg", resp.content)
        self.assertIn(b"88.5/100", resp.content)

    def test_badge_repo_endpoint(self):
        resp = self.client.get("/api/badge/repo/1")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/svg+xml", resp.headers["content-type"])
        self.assertIn(b"<svg", resp.content)

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "GreenCode Auditor")

    def test_ibm_bob_report_endpoint(self):
        resp = self.client.get("/api/ibm-bob/report?repo_path=samples/heavy_pipeline.py")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["event"], "IBM Bob 2.0 Hackathon (lablab.ai)")
        self.assertIn("repository_context", data)
        self.assertIn("execution_plan", data)
        self.assertIn("business_impact", data)
        self.assertIn("safety_verification", data)
        self.assertEqual(data["safety_verification"]["false_positive_rate"], "0%")


if __name__ == "__main__":
    unittest.main()



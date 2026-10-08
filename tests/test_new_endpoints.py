"""Integration tests for new Enterprise Scope, ML, SLA, Pricing, and Prometheus API endpoints."""

import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestEnterpriseEndpoints(unittest.TestCase):
    """Test newly wired enterprise endpoints in app.main."""

    def setUp(self):
        self.client = TestClient(app)

    def test_scope_inventory_api(self):
        payload = {
            "energy_joules": 7200.0,
            "duration_seconds": 2.5,
            "grid_intensity_gco2_per_kwh": 180.0,
            "runs_per_year": 5000,
            "team_size": 4,
            "dev_hours": 160.0,
            "cloud_provider": "aws",
        }
        res = self.client.post("/api/scope/inventory", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("scope_1", data)
        self.assertIn("scope_2", data)
        self.assertIn("scope_3", data)
        self.assertTrue(data["csrd_esrs_e1_aligned"])

    def test_ml_audit_api(self):
        payload = {
            "source_code": "import torch\nloader = DataLoader(d, batch_size=1, num_workers=0)",
            "file_path": "eval.py",
        }
        res = self.client.post("/api/ml/audit", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("ml_green_score", data)
        self.assertIn("violations", data)
        self.assertGreater(data["violations_count"], 0)

    def test_ml_tokens_api(self):
        payload = {
            "parameter_count_b": 13.0,
            "token_count": 2048,
            "hardware": "h100",
            "grid_intensity_gco2_per_kwh": 150.0,
        }
        res = self.client.post("/api/ml/tokens", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("joules_per_token", data)
        self.assertIn("gco2e_per_1k_tokens", data)

    def test_sla_evaluate_api(self):
        payload = {
            "total_joules": 400.0,
            "green_score": 88.0,
            "sci_gco2e": 0.05,
        }
        res = self.client.post("/api/sla/evaluate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["passed"])
        self.assertEqual(data["status"], "COMPLIANT")

    def test_pricing_tiers_api(self):
        res = self.client.get("/api/pricing/tiers")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("free", data)
        self.assertIn("pro", data)
        self.assertIn("enterprise", data)

    def test_prometheus_metrics_endpoint(self):
        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("greencode_http_requests_total", res.text)


if __name__ == "__main__":
    unittest.main()


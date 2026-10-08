"""Unit tests for app.scope (Scope 1-3 ESG) and app.ml_carbon (AI/ML Optimizer)."""

import unittest
from app.scope import ScopeCalculator, ScopeReport
from app.ml_carbon import MLCarbonAnalyzer, MLAnalysisResult, MLTokenCarbonResult


class TestScopeCalculator(unittest.TestCase):
    """Test GHG Protocol Scope 1, 2, and 3 accounting logic."""

    def test_scope_1_calculation(self):
        res = ScopeCalculator.calculate_scope_1(
            team_size=5,
            dev_hours=160.0,
            workstation_watts=100.0,
            grid_intensity_gco2_per_kwh=200.0,
        )
        self.assertEqual(res.team_size, 5)
        # 100W * 160h * 5 = 80,000 Wh = 80 kWh
        self.assertAlmostEqual(res.workstation_energy_kwh, 80.0, places=2)
        # 80 kWh * 200 g/kWh = 16,000 g = 16 kgCO2e
        self.assertAlmostEqual(res.direct_emissions_kgco2e, 16.0, places=2)

    def test_scope_2_dual_accounting(self):
        res = ScopeCalculator.calculate_scope_2(
            energy_kwh_per_run=0.01,
            grid_intensity_gco2_per_kwh=300.0,
            runs_per_year=1000,
            pue=1.2,
            renewable_energy_certificate_pct=50.0,
        )
        # IT: 10 kWh, Facility: 12 kWh
        self.assertAlmostEqual(res.total_energy_kwh_annual, 12.0, places=2)
        # 12 kWh * 300 g/kWh = 3.6 kgCO2e location-based
        self.assertAlmostEqual(res.location_based_kgco2e, 3.6, places=2)
        # 50% renewable -> 1.8 kgCO2e market-based
        self.assertAlmostEqual(res.market_based_kgco2e, 1.8, places=2)

    def test_scope_3_and_inventory_report(self):
        report = ScopeCalculator.generate_inventory(
            energy_joules=3_600_000.0,  # 1 kWh
            duration_seconds=2.0,
            grid_intensity_gco2_per_kwh=200.0,
            runs_per_year=5000,
            cloud_provider="aws",
        )
        self.assertIsInstance(report, ScopeReport)
        self.assertTrue(report.csrd_esrs_e1_aligned)
        self.assertTrue(report.sbti_ict_aligned)
        self.assertIn("scope_1_pct", report.scope_breakdown_pct)
        self.assertGreater(report.total_carbon_kgco2e_annual, 0.0)
        d = report.to_dict()
        self.assertIn("scope_1", d)
        self.assertIn("scope_2", d)
        self.assertIn("scope_3", d)


class TestMLCarbonAnalyzer(unittest.TestCase):
    """Test AI/ML Static Analysis and Token Emission Calculations."""

    def test_detects_ml_anti_patterns(self):
        bad_code = """
import torch
from torch.utils.data import DataLoader

def api_endpoint_handler():
    model = MyModel()
    model.fit(data)  # ML_RETRAINING_IN_ENDPOINT

loader = DataLoader(dataset, batch_size=1, num_workers=0)  # ML_INEFFICIENT_BATCH_SIZE + ML_DATALOADER_CPU_BOTTLENECK

for batch in loader:
    x = batch.to('cuda')  # ML_SYNC_GPU_TENSOR_TRANSFER
    output = model(x)
"""
        res = MLCarbonAnalyzer.audit_code(bad_code, "train.py")
        self.assertIsInstance(res, MLAnalysisResult)
        rules = [v.rule for v in res.violations]
        self.assertIn("ML_RETRAINING_IN_ENDPOINT", rules)
        self.assertIn("ML_INEFFICIENT_BATCH_SIZE", rules)
        self.assertIn("ML_DATALOADER_CPU_BOTTLENECK", rules)
        self.assertIn("ML_SYNC_GPU_TENSOR_TRANSFER", rules)
        self.assertLess(res.ml_green_score, 100.0)
        self.assertIn("PyTorch", res.frameworks_detected)

    def test_clean_ml_code_scores_100(self):
        good_code = """
import torch
from torch.utils.data import DataLoader

loader = DataLoader(dataset, batch_size=64, num_workers=4, pin_memory=True)

with torch.inference_mode():
    for batch in loader:
        pass
"""
        res = MLCarbonAnalyzer.audit_code(good_code, "infer.py")
        self.assertEqual(res.ml_green_score, 100.0)
        self.assertEqual(len(res.violations), 0)

    def test_project_token_emissions(self):
        proj = MLCarbonAnalyzer.project_token_emissions(
            parameter_count_b=7.0,
            token_count=10000,
            hardware="a100",
            grid_intensity_gco2_per_kwh=200.0,
        )
        self.assertIsInstance(proj, MLTokenCarbonResult)
        self.assertGreater(proj.energy_joules, 0.0)
        self.assertGreater(proj.carbon_gco2e, 0.0)
        self.assertGreater(proj.gco2e_per_1k_tokens, 0.0)


if __name__ == "__main__":
    unittest.main()


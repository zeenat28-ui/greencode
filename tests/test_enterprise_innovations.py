"""Unit and regression tests for GreenCode Enterprise Innovations:
1. Kubernetes Pod & Workload Energy Profiler
2. Real-Time IDE Energy Linter (LSP)
3. Energy Debt & Financial Liability Tracker
4. Pre-Production Green Deploy Predictor
5. Multi-Cloud Infrastructure Cost & Carbon Mapper
"""

import pytest

from app.kubernetes_profiler import KubernetesEnergyMonitor, PodEnergySample, RollbackVerdict
from app.energy_linter import EnergyLinter, EnergyDiagnostic
from app.energy_debt import EnergyDebtTracker, TeamEnergyDebt
from app.energy_predictor import GreenDeployPredictor, DeployPredictionResult
from app.cloud_cost_mapper import CloudCostMapper, CloudCostBreakdown


def test_kubernetes_energy_monitor():
    monitor = KubernetesEnergyMonitor(cluster_name="aws-eks-production")
    monitor.record_baseline("payments", "checkout-service", baseline_watts=15.0)

    # 1. Normal pod calculation
    sample = monitor.calculate_pod_energy(
        pod_name="checkout-service-7d89b4f74-xk92m",
        namespace="payments",
        container_name="checkout-api",
        cpu_millicores=350.0,
        memory_bytes=536870912,  # 512MB
        duration_seconds=60.0,
        cloud_instance="c6g.xlarge",
    )
    assert isinstance(sample, PodEnergySample)
    assert sample.power_watts > 0.0
    assert sample.energy_joules > 0.0
    assert sample.annual_cost_usd > 0.0

    # 2. Healthy deployment evaluation
    verdict_ok = monitor.evaluate_deployment_health(
        namespace="payments",
        deployment_name="checkout-service",
        observed_watts=16.5,  # +10% within tolerance
        spike_threshold_pct=35.0,
    )
    assert isinstance(verdict_ok, RollbackVerdict)
    assert verdict_ok.should_rollback is False

    # 3. Critical energy spike evaluation (>35%)
    verdict_spike = monitor.evaluate_deployment_health(
        namespace="payments",
        deployment_name="checkout-service",
        observed_watts=25.0,  # +66.7% spike
        spike_threshold_pct=35.0,
    )
    assert verdict_spike.should_rollback is True
    assert "CRITICAL ENERGY SPIKE" in verdict_spike.reason
    assert verdict_spike.delta_percent > 35.0


def test_energy_linter():
    code_with_issues = """
def process_data(records):
    # Un-cached network in loop and nested loops
    for item in records:
        for sub in item.get('entries', []):
            for leaf in sub.get('nodes', []):
                val = leaf.get('val')
"""
    diagnostics = EnergyLinter.lint_code(code_with_issues, language="python")
    assert isinstance(diagnostics, list)
    assert len(diagnostics) > 0

    diag = diagnostics[0]
    assert isinstance(diag, EnergyDiagnostic)
    assert diag.annual_cost_usd > 0.0
    assert diag.annual_co2_kg > 0.0

    lsp_payload = EnergyLinter.format_lsp_response(diagnostics)
    assert "diagnostics" in lsp_payload
    assert len(lsp_payload["diagnostics"]) > 0
    assert lsp_payload["diagnostics"][0]["source"] == "GreenCode Linter"


def test_energy_debt_tracker():
    tracker = EnergyDebtTracker()
    violations = [
        {"severity": "CRITICAL", "violation_type": "UNCACHED_NETWORK_IN_LOOP", "title": "Network In Loop"},
        {"severity": "HIGH", "violation_type": "NESTED_LOOPS", "title": "Deep Nested Iteration"},
        {"severity": "MEDIUM", "violation_type": "SORTED_IN_LOOP", "title": "Sorting Inside Iteration"},
    ]

    debt = tracker.calculate_team_debt(
        team_id="data-core",
        team_name="Data Core Engineering",
        violations=violations,
        historical_debt_usd=500.0,
    )
    assert isinstance(debt, TeamEnergyDebt)
    assert debt.energy_debt_kg_co2e > 0.0
    assert debt.energy_debt_usd > 0.0
    assert debt.weekly_interest_usd > 0.0
    assert debt.total_violations_count == 3
    assert len(debt.top_offending_patterns) > 0

    assert tracker.get_team_debt("data-core") == debt
    assert len(tracker.list_all_debts()) == 1


def test_green_deploy_predictor():
    base_audit = {"green_score": 96.0, "violations": []}

    # Case 1: Bad PR that drops green score
    bad_incoming = {
        "green_score": 68.0,
        "violations": [{"severity": "CRITICAL"}, {"severity": "HIGH"}],
    }
    pred_bad = GreenDeployPredictor.predict_pr_impact(
        pr_identifier="PR-402",
        base_audit=base_audit,
        incoming_audit=bad_incoming,
    )
    assert isinstance(pred_bad, DeployPredictionResult)
    assert pred_bad.decision == "BLOCK"
    assert pred_bad.energy_delta_percent > 0.0
    assert "MERGE BLOCKED" in pred_bad.recommendation_summary

    # Case 2: Good PR that improves efficiency
    good_base = {"green_score": 80.0, "violations": [{"severity": "HIGH"}]}
    good_incoming = {"green_score": 95.0, "violations": []}
    pred_good = GreenDeployPredictor.predict_pr_impact(
        pr_identifier="PR-403",
        base_audit=good_base,
        incoming_audit=good_incoming,
    )
    assert pred_good.decision == "PASS"
    assert pred_good.energy_delta_percent < 0.0
    assert "APPROVED" in pred_good.recommendation_summary


def test_cloud_cost_mapper():
    # AWS Graviton calculation
    breakdown_aws = CloudCostMapper.calculate_cost(
        provider="aws",
        region="us-west-2",
        service_type="ec2_c6g_xlarge",
        duration_seconds=3600.0,
        energy_joules=72000.0,
    )
    assert isinstance(breakdown_aws, CloudCostBreakdown)
    assert breakdown_aws.provider == "AWS"
    assert breakdown_aws.compute_cost_usd > 0.0
    assert breakdown_aws.electricity_cost_usd > 0.0
    assert breakdown_aws.total_cost_usd > 0.0
    assert breakdown_aws.annualized_run_rate_usd > 0.0
    assert breakdown_aws.total_co2_kg > 0.0

    # GCP Function calculation
    breakdown_gcp = CloudCostMapper.calculate_cost(
        provider="gcp",
        region="us-central1",
        service_type="cloud_functions",
        duration_seconds=10.0,
        energy_joules=250.0,
    )
    assert breakdown_gcp.provider == "GCP"
    assert breakdown_gcp.total_cost_usd > 0.0


def test_kubernetes_live_rollback_execution():
    monitor = KubernetesEnergyMonitor(cluster_name="aws-eks-production")
    monitor.record_baseline("default", "orders-api", baseline_watts=10.0)

    verdict = monitor.evaluate_deployment_health(
        namespace="default",
        deployment_name="orders-api",
        observed_watts=20.0,  # 100% spike
        spike_threshold_pct=30.0,
        auto_trigger_rollback=True,
    )
    assert verdict.should_rollback is True
    assert verdict.rollback_triggered is True
    assert verdict.rollback_status is not None
    assert "ROLLED_BACK_orders-api" in verdict.rollback_status


def test_multi_tenant_carbon_budgets():
    from app.database import (
        set_team_carbon_budget,
        get_team_carbon_budget,
        record_carbon_consumption,
    )

    # 1. Set budget
    b = set_team_carbon_budget(org_id=1, team_id="checkout-eng", monthly_budget_kg=400.0)
    assert b["monthly_budget_kg_co2e"] == 400.0
    assert b["team_id"] == "checkout-eng"

    # 2. Get budget
    fetched = get_team_carbon_budget(org_id=1, team_id="checkout-eng")
    assert fetched is not None
    assert fetched["monthly_budget_kg_co2e"] == 400.0

    # 3. Accrue consumption
    c = record_carbon_consumption(org_id=1, team_id="checkout-eng", consumed_kg=350.0)
    assert c["consumed_kg_co2e"] == 350.0
    assert c["is_breached"] is False
    assert c["utilization_pct"] > 80.0

    # 4. Breach budget
    c_breach = record_carbon_consumption(org_id=1, team_id="checkout-eng", consumed_kg=60.0)
    assert c_breach["is_breached"] is True



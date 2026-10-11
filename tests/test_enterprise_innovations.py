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


def test_sci_joules_to_kwh_physics_conversion():
    from app.sci import compute_sci

    # 1 kWh = 1,000 W * 3,600 s = 3,600,000 Joules
    res = compute_sci(
        energy_joules=3_600_000.0,
        duration_seconds=0.0,
        carbon_intensity_gco2_per_kwh=400.0,
        functional_unit=1.0,
        pue=1.0,
    )
    assert abs(res.energy_kwh - 1.0) < 1e-6
    assert abs(res.operational_gco2 - 400.0) < 1e-4
    assert abs(res.sci_gco2_per_functional_unit - 400.0) < 1e-4


def test_dynamic_violation_energy_span_and_complexity():
    # Two HIGH severity violations with different AST patterns and line spans must produce distinct estimates
    v_nested_cubic = {
        "violation_type": "NESTED_LOOPS_DEPTH_3+",
        "severity": "HIGH",
        "deduction": 15.0,
        "line_number": 10,
        "end_line_number": 22,
    }
    v_cursor = {
        "violation_type": "RAW_DB_CURSOR_NO_CONTEXT",
        "severity": "HIGH",
        "deduction": 10.0,
        "line_number": 30,
        "end_line_number": 31,
    }
    impact_cubic = EnergyDebtTracker.estimate_violation_impact(v_nested_cubic)
    impact_cursor = EnergyDebtTracker.estimate_violation_impact(v_cursor)

    assert impact_cubic["joules_per_1k_calls"] > impact_cursor["joules_per_1k_calls"]
    assert impact_cubic["co2_kg"] > impact_cursor["co2_kg"]
    assert impact_cubic["cost_usd"] > impact_cursor["cost_usd"]


def test_governance_sqlite_persistence_and_residency_enforcement(monkeypatch):
    from app.enterprise_governance import DataResidencyZone, EnterpriseGovernanceManager
    from app.bedrock_client import BedrockClient, BedrockError

    mgr1 = EnterpriseGovernanceManager()
    mgr1.set_data_residency_policy(org_id=77, policy=DataResidencyZone.EU_STRICT)
    mgr1.configure_sso(
        org_id=77,
        idp_entity_id="urn:okta:greencode-eu",
        sso_url="https://login.eu.example.com/sso/saml",
        certificate_x509="-----BEGIN CERTIFICATE-----MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8A-----END CERTIFICATE-----",
        issuer="https://login.eu.example.com",
        allowed_domains=["eu.example.com"],
    )

    # Fresh instance must hydrate from SQLite enterprise_governance_kv table
    mgr2 = EnterpriseGovernanceManager()
    assert mgr2.get_data_residency_policy(77) == DataResidencyZone.EU_STRICT
    sso = mgr2.get_sso_config(77)
    assert sso is not None
    assert sso.idp_entity_id == "urn:okta:greencode-eu"

    # Outbound call to us-east-1 must be blocked for org 77 under EU_STRICT
    monkeypatch.setenv("GREENCODE_ORG_ID", "77")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    client = BedrockClient(region_name="us-east-1", model="anthropic.claude-3-5-haiku-20241022-v1:0")
    with pytest.raises(BedrockError) as exc_info:
        client.chat([{"role": "human", "content": "optimize loop"}])
    assert "GDPR Breach Prevented" in str(exc_info.value)

    # Reset org 77 back to GLOBAL
    mgr2.set_data_residency_policy(org_id=77, policy=DataResidencyZone.GLOBAL)


def test_compliance_runtime_checks_and_retention():
    from app.compliance import ComplianceManager

    posture = ComplianceManager.evaluate_security_posture(org_id=1)
    assert posture["compliance_checks"]["rbac_enforcement"]["passed"] is True
    assert posture["compliance_checks"]["ghg_sci_methodology"]["passed"] is True
    assert "3.6e6 J = 1.0 kWh" in posture["compliance_checks"]["ghg_sci_methodology"]["details"]

    ret = ComplianceManager.enforce_data_retention(retention_days=365, prune_expired=True)
    assert "scan_records_pruned" in ret
    assert "violation_records_pruned" in ret
    assert ret["status"] == "RETENTION_ACTIVE"


def test_parser_complexity_and_kloc_density():
    from app.parser import audit_source_code

    code = """
def cubic(items):
    for a in items:
        for b in items:
            for c in items:
                _ = a + b + c
"""
    res = audit_source_code(code, language="python", file_path="cubic.py")
    assert res["green_score"] < 100.0
    assert "density_adjusted_score" in res
    assert "violations_per_kloc" in res
    assert res["violations_per_kloc"] > 0.0
    assert res["violations"][0]["complexity_class"] == "O(N^3)"
    assert res["violations"][0]["span_lines"] >= 2





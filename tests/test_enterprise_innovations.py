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


def test_aws_cloudwatch_calibrated_energy_bridge():
    from app.calibrated_energy import CalibratedEnergyModel

    class FakeCloudWatchClient:
        def __init__(self, datapoints):
            self._datapoints = datapoints

        def get_metric_statistics(self, **kwargs):
            return {"Datapoints": self._datapoints}

    cw_ok = FakeCloudWatchClient([
        {"Average": 40.0, "Maximum": 75.0},
        {"Average": 60.0, "Maximum": 85.0},
    ])
    res = CalibratedEnergyModel.calculate_from_cloudwatch(
        instance_id="i-0abc123def456",
        cloud_instance="c8g.2xlarge",
        region_name="us-east-1",
        period_seconds=3600,
        memory_mb=16384.0,
        cloudwatch_client=cw_ok,
    )
    assert res.cpu_utilization_pct == 50.0
    assert res.methodology == "AWS_CLOUDWATCH_CALIBRATED_SPECPOWER"
    assert res.confidence_score == 0.92
    assert res.provenance_details["datapoints_sampled"] == 2
    assert res.provenance_details["peak_cpu_utilization_pct"] == 85.0

    # Empty datapoints must fail closed rather than fabricating numbers
    cw_empty = FakeCloudWatchClient([])
    with pytest.raises(RuntimeError) as exc_info:
        CalibratedEnergyModel.calculate_from_cloudwatch(
            instance_id="i-0empty000000",
            cloudwatch_client=cw_empty,
        )
    assert "Refusing to fabricate telemetry" in str(exc_info.value)


def test_aws_graviton_migration_roi_engine():
    comp = CloudCostMapper.compare_graviton_migration(
        source_x86_instance="m5.2xlarge",
        target_graviton_instance="c8g.2xlarge",
        cpu_utilization_pct=60.0,
        memory_mb=16384.0,
        region="us-east-1",
        instance_count=10,
    )
    assert comp.instance_count == 10
    assert comp.target_graviton_instance == "c8g.2xlarge"
    assert 40.0 <= comp.energy_reduction_pct <= 68.0
    assert comp.annual_kwh_saved > 0.0
    assert comp.annual_usd_saved > 0.0
    assert comp.annual_co2_saved_kg > 0.0


def test_bedrock_sci_for_ai_token_metering():
    from app.bedrock_client import BedrockClient
    from app.huggingface_client import LLMUsage

    usage = LLMUsage(prompt_tokens=1000, completion_tokens=500)
    sonnet_fp = BedrockClient.compute_inference_footprint(
        usage=usage,
        model_id="anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name="us-east-1",
        duration_seconds=1.5,
    )
    haiku_fp = BedrockClient.compute_inference_footprint(
        usage=usage,
        model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
        region_name="us-east-1",
        duration_seconds=0.6,
    )

    # 1,000 input * $0.003/1k + 500 output * $0.015/1k = $0.0105
    assert abs(sonnet_fp["estimated_cost_usd"] - 0.0105) < 1e-6
    # 1,000 input * $0.0008/1k + 500 output * $0.004/1k = $0.0028
    assert abs(haiku_fp["estimated_cost_usd"] - 0.0028) < 1e-6
    assert sonnet_fp["it_energy_joules"] > haiku_fp["it_energy_joules"]
    assert sonnet_fp["sci_gco2_per_1k_tokens"] > 0.0


def test_us_eia_930_hourly_grid_carbon_provider(monkeypatch):
    import app.carbon_intensity as ci

    sample_eia_payload = {
        "response": {
            "data": [
                {"period": "2026-10-11T16", "respondent": "PJM", "fueltype": "NG", "value": "40000"},
                {"period": "2026-10-11T16", "respondent": "PJM", "fueltype": "NUC", "value": "30000"},
                {"period": "2026-10-11T16", "respondent": "PJM", "fueltype": "COL", "value": "10000"},
                {"period": "2026-10-11T16", "respondent": "PJM", "fueltype": "WND", "value": "20000"},
            ]
        }
    }
    monkeypatch.setattr(ci, "_get_json", lambda url, headers=None, timeout=6.0: (sample_eia_payload, None))

    res = ci.resolve_carbon_intensity(
        zone="US-MIDA-PJM",
        use_cache=False,
        key_override={"EIA_API_KEY": "eia-test-key-123"},
    )
    assert res.is_live is True
    assert res.intensity_source == "us_eia_930"
    assert res.intensity_source_tier == ci.TIER_PRIMARY_OFFICIAL
    # Weighted: (40000*490 + 30000*12 + 10000*995 + 20000*11) / 100000 = 301.3 gCO2/kWh
    assert abs(res.carbon_intensity - 301.3) < 0.2


def test_cross_function_call_graph_loop_detection_and_git_diff_audit():
    from app.parser import audit_source_code, audit_git_diff

    code_with_helper_chain = """
import requests

def low_level_http(endpoint):
    return requests.get(endpoint)

def fetch_customer_profile(cid):
    return low_level_http(f"https://api.example.com/customers/{cid}")

def sync_all_customers(customer_ids):
    results = []
    for cid in customer_ids:
        results.append(fetch_customer_profile(cid))
    return results
"""
    res = audit_source_code(code_with_helper_chain, language="python", file_path="sync.py")
    vtypes = [v["violation_type"] for v in res["violations"]]
    assert "UNCACHED_NETWORK_IN_LOOP" in vtypes
    chain_Violation = [v for v in res["violations"] if v["violation_type"] == "UNCACHED_NETWORK_IN_LOOP"][0]
    assert "fetch_customer_profile()" in chain_Violation["description"]
    assert "low_level_http()" in chain_Violation["description"]

    # Unified Git Diff audit: file has a pre-existing violation at lines 4-8, and a newly added violation at lines 16-18
    full_file = """import requests

def legacy_func(urls):
    for u in urls:
        requests.get(u)

def clean_func(x):
    return x * 2

def new_pr_func(items):
    out = ""
    for item in items:
        out += str(item)
    return out
"""
    unified_diff = """diff --git a/service.py b/service.py
index 1111111..2222222 100644
--- a/service.py
+++ b/service.py
@@ -10,5 +10,5 @@ def clean_func(x):
 def new_pr_func(items):
     out = ""
     for item in items:
+        out += str(item)
     return out
"""
    diff_audit = audit_git_diff(unified_diff, source_files={"service.py": full_file})
    assert diff_audit["modified_files_count"] == 1
    assert diff_audit["total_diff_violations"] == 1
    assert diff_audit["violations"][0]["violation_type"] == "QUADRATIC_STRING_CONCAT_IN_LOOP"
    assert diff_audit["violations"][0]["diff_scoped"] is True


def test_cncf_kepler_prometheus_metrics_parser():
    monitor = KubernetesEnergyMonitor(cluster_name="eks-prod")
    monitor.record_baseline("payments", "ledger-api", baseline_watts=20.0)

    kepler_exposition = """
# HELP kepler_container_joules_total Total energy in Joules consumed by container via RAPL/eBPF
# TYPE kepler_container_joules_total counter
kepler_container_joules_total{container_name="ledger",container_namespace="payments",mode="dynamic",pod_name="ledger-api-7f9c8b-x2k"} 1500.0
kepler_container_joules_total{container_name="ledger",container_namespace="payments",mode="idle",pod_name="ledger-api-7f9c8b-x2k"} 300.0
container_memory_working_set_bytes{container="ledger",namespace="payments",pod="ledger-api-7f9c8b-x2k"} 268435456
"""
    samples = monitor.parse_prometheus_kepler_metrics(kepler_exposition, duration_seconds=60.0)
    assert len(samples) == 1
    s = samples[0]
    assert s.pod_name == "ledger-api-7f9c8b-x2k"
    assert s.namespace == "payments"
    assert abs(s.energy_joules - 1800.0) < 1e-3
    assert abs(s.power_watts - 30.0) < 1e-3  # 1800 J / 60 s = 30 W (> 20W * 1.25 baseline -> anomaly!)
    assert s.anomaly_detected is True
    assert "Kepler eBPF/RAPL telemetry spike" in (s.anomaly_reason or "")


def test_saml_20_xml_assertion_verification_and_xxe_defense():
    import base64
    from datetime import datetime, timedelta, timezone
    from app.enterprise_governance import EnterpriseGovernanceManager

    mgr = EnterpriseGovernanceManager()
    pinned_cert = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIDXTCCAkWgAwIBAgIJALa8X9z1EXAMPLECERTBODY1234567890\n"
        "-----END CERTIFICATE-----"
    )
    mgr.configure_sso(
        org_id=88,
        idp_entity_id="http://www.okta.com/exk88greencode",
        sso_url="https://acme.okta.com/app/greencode/sso/saml",
        certificate_x509=pinned_cert,
        issuer="http://www.okta.com/exk88greencode",
        allowed_domains=["acme.com"],
    )

    now = datetime.now(timezone.utc)
    nb = (now - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    noa = (now + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

    valid_saml_xml = f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <saml:Issuer>http://www.okta.com/exk88greencode</saml:Issuer>
  <ds:Signature>
    <ds:KeyInfo>
      <ds:X509Data>
        <ds:X509Certificate>MIIDXTCCAkWgAwIBAgIJALa8X9z1EXAMPLECERTBODY1234567890</ds:X509Certificate>
      </ds:X509Data>
    </ds:KeyInfo>
  </ds:Signature>
  <saml:Assertion>
    <saml:Subject>
      <saml:NameID>architect@acme.com</saml:NameID>
    </saml:Subject>
    <saml:Conditions NotBefore="{nb}" NotOnOrAfter="{noa}" />
  </saml:Assertion>
</samlp:Response>"""

    b64_payload = base64.b64encode(valid_saml_xml.encode("utf-8")).decode("ascii")
    res_ok = mgr.verify_saml_response(org_id=88, saml_response_b64=b64_payload)
    assert res_ok["verified"] is True
    assert res_ok["subject_name_id"] == "architect@acme.com"
    assert len(res_ok["cert_sha256_fingerprint"]) == 64

    # Unauthorized email domain must be rejected
    bad_domain_xml = valid_saml_xml.replace("architect@acme.com", "intruder@evil.org")
    res_dom = mgr.verify_saml_response(org_id=88, saml_response_b64=bad_domain_xml)
    assert res_dom["verified"] is False
    assert "allowed_domains" in res_dom["reason"]

    # XXE / DOCTYPE payload must be blocked
    xxe_xml = '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>' + valid_saml_xml
    res_xxe = mgr.verify_saml_response(org_id=88, saml_response_b64=xxe_xml)
    assert res_xxe["verified"] is False
    assert "DTD/ENTITY" in res_xxe["reason"]


def test_csrd_audit_evidence_zip_bundle_and_s3_worm_archival():
    import hashlib
    import io
    import json
    import zipfile
    from app.reports.esg_report import ESGReportGenerator
    from app.compliance import ComplianceManager

    zip_bytes, manifest = ESGReportGenerator.generate_evidence_bundle(org_id=1, period="2026-10")
    assert len(zip_bytes) > 200
    assert len(manifest["bundle_root_sha256"]) == 64

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = set(zf.namelist())
        assert {
            "esg_disclosure.json",
            "esg_disclosure.html",
            "underlying_telemetry.csv",
            "audit_chain_certificate.json",
            "manifest.sha256.json",
        }.issubset(names)
        for fname, expected_digest in manifest["file_digests"].items():
            actual_digest = hashlib.sha256(zf.read(fname)).hexdigest()
            assert actual_digest == expected_digest

    class FakeS3WORMClient:
        def __init__(self):
            self.last_kwargs = None

        def put_object(self, **kwargs):
            self.last_kwargs = kwargs
            return {"ETag": '"worm-etag-123"', "VersionId": "v-worm-001"}

    s3_stub = FakeS3WORMClient()
    worm_res = ComplianceManager.export_audit_chain_to_s3_worm(
        org_id=1,
        bucket_name="greencode-sec-csrd-worm-vault",
        retention_days=2555,  # 7-year SOX/CSRD retention
        s3_client=s3_stub,
    )
    assert worm_res["archived"] is True
    assert worm_res["object_lock_mode"] == "COMPLIANCE"
    assert s3_stub.last_kwargs["ObjectLockMode"] == "COMPLIANCE"
    assert len(worm_res["sha256_hex"]) == 64


def test_aws_marketplace_batch_meter_usage_sync():
    from app.services.billing_service import BillingService

    BillingService.consume(org_id=1, tier="enterprise", event_type="api_call")

    class FakeMarketplaceClient:
        def __init__(self):
            self.calls = []

        def batch_meter_usage(self, **kwargs):
            self.calls.append(kwargs)
            return {
                "Results": [
                    {
                        "MeteringRecordId": "mp-rec-998877",
                        "Status": "Success",
                    }
                ],
                "UnprocessedRecords": [],
            }

    mp_client = FakeMarketplaceClient()
    sync_res = BillingService.sync_usage_to_aws_marketplace(
        org_id=1,
        product_code="prod-greencode-enterprise",
        customer_identifier="cust-amzn-001",
        dimension="api_calls",
        metering_client=mp_client,
    )
    assert sync_res["metered"] is True
    assert sync_res["metering_record_id"] == "mp-rec-998877"
    assert sync_res["quantity"] >= 1
    assert mp_client.calls[0]["ProductCode"] == "prod-greencode-enterprise"


def test_kepler_prometheus_parser_does_not_double_count_rapl_hierarchy():
    monitor = KubernetesEnergyMonitor(cluster_name="eks-prod")
    # Container 1 reports total (120J) AND sub-domains (package=100J, core=80J, dram=20J) -> must be 120J, NOT 320J
    # Container 2 reports package (60J), core (50J), and dram (15J) without total -> must be 60+15 = 75J, NOT 125J
    metrics = """
    kepler_container_joules_total{container_namespace="prod",pod_name="api-1",container_name="app",mode="dynamic"} 120.0
    kepler_container_package_joules_total{container_namespace="prod",pod_name="api-1",container_name="app"} 100.0
    kepler_container_core_joules_total{container_namespace="prod",pod_name="api-1",container_name="app"} 80.0
    kepler_container_dram_joules_total{container_namespace="prod",pod_name="api-1",container_name="app"} 20.0
    kepler_container_package_joules_total{container_namespace="prod",pod_name="worker-1",container_name="job"} 60.0
    kepler_container_core_joules_total{container_namespace="prod",pod_name="worker-1",container_name="job"} 50.0
    kepler_container_dram_joules_total{container_namespace="prod",pod_name="worker-1",container_name="job"} 15.0
    """
    samples = monitor.parse_prometheus_kepler_metrics(metrics, duration_seconds=60.0)
    by_pod = {s.pod_name: s for s in samples}
    # 120 J over 60s = 2.0 W
    assert abs(by_pod["api-1"].energy_joules - 120.0) < 1e-4
    assert abs(by_pod["api-1"].power_watts - 2.0) < 1e-4
    # 75 J over 60s = 1.25 W
    assert abs(by_pod["worker-1"].energy_joules - 75.0) < 1e-4
    assert abs(by_pod["worker-1"].power_watts - 1.25) < 1e-4


def test_cloud_cost_mapper_gcp_and_azure_rates_and_regions():
    gcp_vm = CloudCostMapper.calculate_cost(
        provider="gcp",
        region="us-west1",
        service_type="e2_standard_4",
        duration_seconds=3600.0,
        energy_joules=36000.0,
    )
    assert gcp_vm.provider == "GCP"
    assert abs(gcp_vm.compute_cost_usd - 0.1340) < 1e-4
    assert abs(gcp_vm.carbon_intensity_g_per_kwh - 140.0) < 1e-4

    azure_vm = CloudCostMapper.calculate_cost(
        provider="azure",
        region="swedencentral",
        service_type="Standard_D4s_v5",
        duration_seconds=3600.0,
        energy_joules=36000.0,
    )
    assert azure_vm.provider == "AZURE"
    assert abs(azure_vm.compute_cost_usd - 0.1920) < 1e-4
    assert abs(azure_vm.carbon_intensity_g_per_kwh - 18.0) < 1e-4


def test_part4_validator_and_gatekeeper_hardening(tmp_path):
    from app.profiler import validate_script_safety_for_host
    from app.services.energy_policy_service import EnergyPolicyService
    from app.services.energy_diff_service import EnergyDiffService
    from app.kubernetes_profiler import trigger_kubernetes_rollback

    # 1. Host AST safety guard blocks aliased subprocess, from-imported os.system, and eval()
    for idx, bad_code in enumerate([
        "import subprocess as sp\nsp.run(['echo', 'pwn'])\n",
        "from os import system as run_cmd\nrun_cmd('whoami')\n",
        "x = eval('1 + 1')\n",
        "def broken_syntax(:\n    pass\n",
    ]):
        p = tmp_path / f"bad_{idx}.py"
        p.write_text(bad_code, encoding="utf-8")
        err = validate_script_safety_for_host(str(p))
        assert err is not None and "Blocked" in err

    safe_p = tmp_path / "safe.py"
    safe_p.write_text("total = sum(i * i for i in range(100))\n", encoding="utf-8")
    assert validate_script_safety_for_host(str(safe_p)) is None

    # 2. EnergyPolicyService enforces max_sci_gco2e ceiling and persists policy in SQLite
    EnergyPolicyService.set_policy(
        project_id=909,
        policy={
            "max_energy_regression_pct": 15.0,
            "min_green_score": 70.0,
            "max_sci_gco2e": 10.0,
        },
        org_id=1,
    )
    gate_sci_breach = EnergyPolicyService.evaluate_deployment_gate(
        project_id=909,
        current_metrics={"energy_joules": 102.0, "green_score": 88.0, "sci_gco2e": 14.5},
        baseline_metrics={"energy_joules": 100.0},
        grid_intensity=300.0,
    )
    assert gate_sci_breach["gate_status"] == "BLOCKED"
    assert gate_sci_breach["is_blocked"] is True
    assert gate_sci_breach["current_sci_gco2e"] == 14.5
    assert any("SCI score" in r for r in gate_sci_breach["violations"])

    # 3. EnergyDiffService uses physics-calibrated CloudCostMapper instead of dummy 180x/42x
    diff_res = EnergyDiffService.compare_scans(
        base_scan={
            "id": 1,
            "green_score": 72.0,
            "energy_joules": 50.0,
            "sci_gco2e": 8.0,
            "violations": [{"violation_type": "NESTED_LOOPS", "severity": "HIGH"}],
        },
        head_scan={
            "id": 2,
            "green_score": 94.0,
            "energy_joules": 20.0,
            "sci_gco2e": 3.2,
            "violations": [],
        },
        grid_zone="eu-north-1",
    )
    assert diff_res["verdict"] == "APPROVED"
    assert diff_res["energy_delta_pct"] == -60.0
    assert diff_res["annual_cost_delta_usd"] < 0.0
    assert diff_res["annual_carbon_delta_kg"] < 0.0

    # 4. EnergyLinter populates quick_fix_code and exposes it in LSP payload
    diags = EnergyLinter.lint_code(
        "def f(items):\n    out = ''\n    for x in items:\n        out += str(x)\n    return out\n",
        language="python",
    )
    assert len(diags) > 0
    assert diags[0].quick_fix_code is not None
    lsp = EnergyLinter.format_lsp_response(diags)
    assert lsp["diagnostics"][0]["data"]["quick_fix_code"] is not None

    # 5. trigger_kubernetes_rollback reports LOCAL_EMULATION when outside live cluster
    rb = trigger_kubernetes_rollback("default", "checkout-api")
    assert rb["status"] in ("LOCAL_EMULATION", "SUCCESS")


def test_spine_memory_and_lawyer_upgrades():
    """Verify Part 7 (Spine, Memory & Lawyer) upgrades: SHA-256 tamper detection, ESG bundle, budget & billing guards."""
    import json
    import pytest
    from app.audit_logs import AuditLogManager
    from app.database import AuditLog, Repository, SessionLocal, reset_password_with_token
    from app.reports.esg_report import ESGReportGenerator
    from app.services.billing_service import BillingService
    from app.services.budget_service import BudgetService

    # 1. AuditLogManager.verify_integrity detects payload tampering even if prev_hash & record_hash are untouched
    org_id = 77701
    db = SessionLocal()
    try:
        db.query(AuditLog).filter(AuditLog.org_id == org_id).delete()
        db.commit()
    finally:
        db.close()

    ev = AuditLogManager.record_event(
        org_id=org_id,
        action="budget:allocate",
        resource_type="carbon_budget",
        resource_id="core:2026-10",
        details={"monthly_budget_kg": 500.0},
    )
    assert AuditLogManager.verify_integrity(org_id)["valid"] is True

    # Tamper with the stored payload without changing prev_hash or record_hash
    db = SessionLocal()
    try:
        row = db.query(AuditLog).filter(AuditLog.id == ev["id"]).first()
        tampered = json.loads(row.details)
        tampered["monthly_budget_kg"] = 999999.0
        row.details = json.dumps(tampered, sort_keys=True)
        db.commit()
    finally:
        db.close()

    tamper_check = AuditLogManager.verify_integrity(org_id)
    assert tamper_check["valid"] is False
    assert tamper_check["error"] == "RECORD_HASH_TAMPERED"

    # Clean up tampered row
    db = SessionLocal()
    try:
        db.query(AuditLog).filter(AuditLog.org_id == org_id).delete()
        # 2. ESGReportGenerator.generate_evidence_bundle works when org has Repository rows
        repo = Repository(
            org_id=org_id,
            name="acme/core-engine",
            path_or_url="https://github.com/acme/core-engine",
            total_files=12,
            total_lines=1400,
            green_score=91.5,
        )
        db.add(repo)
        db.commit()
    finally:
        db.close()

    zip_bytes, manifest = ESGReportGenerator.generate_evidence_bundle(org_id=org_id)
    assert len(zip_bytes) > 200
    assert manifest["audit_ledger_verified"] is True
    esg_data = ESGReportGenerator.generate_data(org_id=org_id)
    assert "scope_2_tonnes_co2e" in esg_data
    assert "scope_3_tonnes_co2e" in esg_data

    # 3. BudgetService.get_team_status & evaluate_pr_impact auto-initialize fresh team budget without crashing
    fresh_status = BudgetService.get_team_status(org_id=org_id, team_id="new-unallocated-team")
    assert fresh_status["monthly_budget_kg_co2e"] == 500.0
    pr_impact = BudgetService.evaluate_pr_impact(
        org_id=org_id, team_id="new-unallocated-team", additional_projected_kg_co2e=15.0
    )
    assert pr_impact["verdict"] == "PASSED"

    # 4. BillingService rejects unknown tiers and sets a 30-day billing period
    with pytest.raises(KeyError):
        BillingService.change_tier(org_id=org_id, new_tier="nonexistent_platinum_tier")
    sub = BillingService.change_tier(org_id=org_id, new_tier="pro")
    assert sub["tier"] == "pro"
    assert sub["current_period_end"] > sub["current_period_start"]

    # 5. reset_password_with_token enforces 12-char 3-class password policy
    weak_res = reset_password_with_token("any-token", "weakpass1")
    assert weak_res["success"] is False
    assert "12 characters" in weak_res["error"]


def test_full_seven_part_end_to_end_integration(tmp_path):
    """Verify all 7 architectural subsystems (Eyes -> Ears -> Brain -> Hands -> Legs -> Voice -> Spine) integrate end-to-end."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.parser import audit_source_code
    from app.carbon_intensity import get_zone_carbon_intensity
    from app.calibrated_energy import CalibratedEnergyModel
    from app.energy_predictor import GreenDeployPredictor
    from app.services.energy_diff_service import EnergyDiffService
    from app.amazon_service import get_region_carbon_intensity, list_available_regions
    from app.esg_disclosure import ESGComplianceExporter
    from app.database import get_latest_repositories, SessionLocal, Project
    from app.audit.service import AuditService

    # Part 1 (Eyes): Scan inefficient vs optimized Python code
    bad_code = (
        "def calc(items):\n"
        "    out = ''\n"
        "    for i in items:\n"
        "        for j in items:\n"
        "            for k in items:\n"
        "                out = out + str(i) + str(j) + str(k)\n"
        "    return out\n"
    )
    good_code = "def calc(items):\n    return ''.join(f'{i}{j}{k}' for i in items for j in items for k in items)\n"
    base_scan = audit_source_code(good_code, "python")
    head_scan = audit_source_code(bad_code, "python")
    assert head_scan["green_score"] < base_scan["green_score"]

    # Part 2 (Ears & Sensors): Fetch grid intensity & derive calibrated energy
    grid = get_zone_carbon_intensity("IE")
    assert grid["carbon_intensity"] > 0
    cal = CalibratedEnergyModel.calculate_energy(duration_seconds=1.2, cpu_utilization_pct=55.0, cloud_instance="c6g.xlarge")
    assert cal.energy_joules > 0

    # Part 3 (Brain): Predict PR impact and cloud cost
    pred = GreenDeployPredictor.predict_pr_impact("PR-777", base_scan, head_scan)
    assert pred.energy_delta_percent > 0
    assert pred.decision in ("PASS", "WARN", "BLOCK")

    # Part 4 (Hands): Evaluate PR Energy Diff Gate
    diff_gate = EnergyDiffService.compare_scans(
        base_scan=base_scan,
        head_scan=head_scan,
        grid_zone="IE",
        instance_type="c6g.xlarge",
    )
    assert diff_gate["verdict"] in ("BLOCKED", "WARNING", "PASSED")
    assert "pr_markdown_comment" in diff_gate

    # Part 5 (Legs): Compare AWS region intensities (Ember 2024 cited fallback / live grid)
    se_region = get_region_carbon_intensity("eu-north-1")
    us_region = get_region_carbon_intensity("us-east-1")
    assert se_region["carbon_intensity"] < us_region["carbon_intensity"]
    assert "eu-north-1" in list_available_regions()

    # Part 6 & Part 7 (Voice/Face + Spine/Memory/Lawyer) via FastAPI TestClient
    client = TestClient(app)

    # /api/repositories (used by Overview.tsx)
    repos_resp = client.get("/api/repositories?limit=5")
    assert repos_resp.status_code == 200
    repos_json = repos_resp.json()
    assert "repositories" in repos_json
    assert isinstance(repos_json["repositories"], list)

    # /api/energy/budgets (used by Overview.tsx and Budgets.tsx)
    budgets_resp = client.get("/api/energy/budgets?org_id=1&team_id=core-infra")
    assert budgets_resp.status_code == 200
    budgets_json = budgets_resp.json()
    assert "budgets" in budgets_json
    assert isinstance(budgets_json["budgets"], list)
    assert len(budgets_json["budgets"]) >= 1
    assert "monthly_budget_kg" in budgets_json["budgets"][0]
    assert "current_consumed_kg" in budgets_json["budgets"][0]

    # /api/voice/ask (used by AlexaVoiceCockpit.tsx) - verify all 4 branches work even when DB has repositories
    for query_text in ("which region is cleanest?", "refactor loop with bedrock", "explain provenance score", "audit repository"):
        v_resp = client.post("/api/voice/ask", json={"query": query_text, "zone": "IE"})
        assert v_resp.status_code == 200
        v_data = v_resp.json()
        assert v_data["success"] is True
        assert "mcp_envelope" in v_data

    # ESGComplianceExporter handles get_latest_repositories() paginated dict directly
    latest_page = get_latest_repositories(limit=5)
    disclosure = ESGComplianceExporter.generate_disclosure_package(
        organization={"name": "Acme Corp", "slug": "acme"},
        audits=latest_page,
    )
    assert disclosure.report_id.startswith("CSRD-GC-")

    # AuditService.execute_audit & get_project_audits work cleanly with a real Project row
    sample_file = tmp_path / "service_check.py"
    sample_file.write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
    db = SessionLocal()
    try:
        proj = Project(org_id=1, name="sync-check-service", slug="sync-check-service")
        db.add(proj)
        db.commit()
        db.refresh(proj)
        proj_id = proj.id
    finally:
        db.close()

    exec_res = AuditService.execute_audit(path=str(sample_file), project_id=proj_id)
    assert exec_res["green_score"] == 100.0
    hist_res = AuditService.get_project_audits(project_id=proj_id)
    assert len(hist_res) >= 1
    assert hist_res[0]["name"] == "sync-check-service"









"""Enterprise Platform Test Suite.

Validates multi-tenancy models, RBAC permissions, carbon budgeting & forecasting,
Kubernetes rollback controllers, pre-deploy PR energy diff gates, cryptographic audit trails,
and ESG reporting exports.
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.auth.roles import Role, Permission, has_permission, normalize_role
from app.services.org_service import OrgService
from app.services.budget_service import BudgetService
from app.services.rollback_service import RollbackService
from app.services.energy_policy_service import EnergyPolicyService
from app.services.energy_diff_service import EnergyDiffService
from app.audit_logs import AuditLogManager
from app.reports.esg_report import ESGReportGenerator
from app.compliance import ComplianceManager


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def test_rbac_matrix_and_normalization():
    """Verify role permissions and safe role normalization."""
    assert normalize_role("admin") == Role.ORG_ADMIN
    assert normalize_role("org_admin") == Role.ORG_ADMIN
    assert normalize_role("engineer") == Role.DEVELOPER
    assert normalize_role("superadmin") == Role.SUPERADMIN

    # Permission checks
    assert has_permission(Role.ORG_ADMIN.value, Permission.MANAGE_ORG) is True
    assert has_permission(Role.ORG_ADMIN.value, Permission.EXECUTE_ROLLBACK) is True
    assert has_permission(Role.DEVELOPER.value, Permission.MANAGE_ORG) is False
    assert has_permission(Role.DEVELOPER.value, Permission.READ_METRICS) is True
    assert has_permission(Role.AUDITOR.value, Permission.EXPORT_ESG) is True
    assert has_permission(Role.AUDITOR.value, Permission.EXECUTE_ROLLBACK) is False


def test_multi_tenancy_service():
    """Verify org, team, project creation and association."""
    org = OrgService.create_organization(
        name="Test Enterprise Inc",
        slug="test-ent-unique",
        tier="enterprise",
        sso_enabled=True,
    )
    assert org["id"] is not None
    assert org["slug"] == "test-ent-unique"

    team = OrgService.create_team(
        org_id=org["id"],
        name="Platform Team",
        slug="platform-team",
        monthly_carbon_budget_kg=600.0,
    )
    assert team["id"] is not None
    assert team["monthly_carbon_budget_kg"] == 600.0

    project = OrgService.create_project(
        org_id=org["id"],
        name="Checkout Microservice",
        slug="checkout-ms",
        team_id=team["id"],
        sci_threshold=85.0,
        energy_budget_kwh=40.0,
    )
    assert project["id"] is not None
    assert project["sci_threshold"] == 85.0

    teams_list = OrgService.list_teams(org["id"])
    assert len(teams_list) >= 1

    projects_list = OrgService.list_projects(org["id"])
    assert len(projects_list) >= 1


def test_carbon_budget_lifecycle_and_alerts():
    """Verify budget allocation, threshold alerts (70%, 90%, 100%), and PR gate check."""
    org_id = 99
    team_id = "billing-infra"

    # Allocate 100 kg
    BudgetService.allocate_budget(
        org_id=org_id,
        team_id=team_id,
        monthly_budget_kg=100.0,
        period="2026-10",
    )

    # Initial state (0% consumed) -> NORMAL
    status = BudgetService.get_team_status(org_id=org_id, team_id=team_id, period="2026-10")
    assert status["alert_level"] == "NORMAL"
    assert status["consumed_kg_co2e"] == 0.0

    # Consume 75 kg (75%) -> WARNING (70% - 89.9%)
    BudgetService.record_emission(org_id=org_id, team_id=team_id, consumed_kg=75.0, period="2026-10")
    status_75 = BudgetService.get_team_status(org_id=org_id, team_id=team_id, period="2026-10")
    assert status_75["alert_level"] == "WARNING"

    # Consume another 20 kg (total 95 kg, 95%) -> CRITICAL (90% - 99.9%)
    BudgetService.record_emission(org_id=org_id, team_id=team_id, consumed_kg=20.0, period="2026-10")
    status_95 = BudgetService.get_team_status(org_id=org_id, team_id=team_id, period="2026-10")
    assert status_95["alert_level"] == "CRITICAL"

    # Test pre-deployment PR impact: adding 10 kg would breach 100 kg limit
    pr_eval = BudgetService.evaluate_pr_impact(
        org_id=org_id,
        team_id=team_id,
        additional_projected_kg_co2e=10.0,
        period="2026-10",
    )
    assert pr_eval["will_breach"] is True
    assert pr_eval["blocks_merge"] is True
    assert pr_eval["verdict"] == "BLOCKED"


def test_kubernetes_rollback_service():
    """Verify live rollback service triggering on critical power spike."""
    result = RollbackService.evaluate_and_rollback(
        namespace="production",
        deployment_name="auth-service",
        current_power_w=280.0,
        baseline_power_w=150.0,
        auto_trigger=True,
    )
    assert result["spike_pct"] > 35.0
    assert result["verdict"] == "CRITICAL_SPIKE"
    assert result["rollback_triggered"] is True
    assert "status" in result["rollback_status"]


def test_energy_diff_service_and_pr_gate():
    """Verify pre-deploy PR energy diff calculation and merge gate blocking."""
    base_scan = {
        "total_energy_joules": 0.05,
        "green_score": 95.0,
    }
    # Head with 40% energy regression
    head_scan_bad = {
        "total_energy_joules": 0.07,
        "green_score": 75.0,
    }

    eval_bad = EnergyDiffService.compare_scans(
        base_scan=base_scan,
        head_scan=head_scan_bad,
        max_regression_pct=15.0,
    )
    assert eval_bad["is_blocked"] is True
    assert eval_bad["verdict"] == "BLOCKED"
    assert "🔴 FAILED - MERGE BLOCKED" in eval_bad["pr_markdown_comment"]
    assert eval_bad["annual_cost_delta_usd"] > 0

    # Head with 5% optimization
    head_scan_good = {
        "total_energy_joules": 0.045,
        "green_score": 98.0,
    }
    eval_good = EnergyDiffService.compare_scans(
        base_scan=base_scan,
        head_scan=head_scan_good,
        max_regression_pct=15.0,
    )
    assert eval_good["is_blocked"] is False
    assert eval_good["verdict"] == "APPROVED"
    assert "🟢 PASSED - GREEN VERIFIED" in eval_good["pr_markdown_comment"]


def test_cryptographic_audit_trail_and_esg_reports():
    """Verify SHA-256 hash chaining of audit trail and ESG HTML disclosure generation."""
    org_id = 77
    ev1 = AuditLogManager.record_event(
        org_id=org_id,
        action="policy:create",
        resource_type="policy",
        resource_id="pol-1",
        details={"rule": "max_regression_15"},
    )
    assert ev1["record_hash"] is not None

    ev2 = AuditLogManager.record_event(
        org_id=org_id,
        action="k8s:rollback",
        resource_type="deployment",
        resource_id="prod/payments",
        details={"spike": 42.0},
    )
    assert ev2["prev_hash"] == ev1["record_hash"]

    # Verify integrity of chain
    integrity = AuditLogManager.verify_integrity(org_id)
    assert integrity["valid"] is True
    assert integrity["status"] == "CHAIN_VERIFIED_TAMPER_EVIDENT"

    # ESG report generation
    esg_data = ESGReportGenerator.generate_data(org_id=org_id)
    assert "standards_compliance" in esg_data
    assert esg_data["emissions_summary"]["total_energy_consumption_kwh"] > 0

    esg_html = ESGReportGenerator.generate_html(org_id=org_id)
    assert "<!DOCTYPE html>" in esg_html
    assert "Enterprise Carbon & Energy Disclosure Report" in esg_html


def test_enterprise_rest_endpoints(client):
    """Verify FastAPI endpoints for orgs, energy deployment, budgets, pr-gate, and reports."""
    # 1. Org creation endpoint
    res_org = client.post("/api/orgs", json={
        "name": "Acme SaaS Corp",
        "slug": "acme-saas-corp",
        "tier": "enterprise",
    })
    assert res_org.status_code in (200, 201)
    org_id = res_org.json()["id"]

    # 2. Energy policy endpoint
    res_pol = client.post("/api/energy/policy", json={
        "project_id": 1,
        "policy": {"max_energy_regression_pct": 12.0},
    })
    assert res_pol.status_code == 200
    assert res_pol.json()["max_energy_regression_pct"] == 12.0

    # 3. Energy rollback endpoint
    res_rb = client.post("/api/energy/rollback", json={
        "namespace": "production",
        "deployment_name": "payments-api",
        "current_power_w": 290.0,
        "baseline_power_w": 180.0,
        "auto_trigger": True,
    })
    assert res_rb.status_code == 200
    assert res_rb.json()["rollback_triggered"] is True

    # 4. PR gate evaluation endpoint
    res_gate = client.post("/api/pr-gate/evaluate", json={
        "base_scan": {"total_energy_joules": 0.05, "green_score": 95.0},
        "head_scan": {"total_energy_joules": 0.045, "green_score": 98.0},
        "max_regression_pct": 15.0,
    })
    assert res_gate.status_code == 200
    assert res_gate.json()["verdict"] == "APPROVED"

    # 5. ESG report export endpoint
    res_esg = client.get(f"/api/reports/esg/{org_id}")
    assert res_esg.status_code == 200
    assert "emissions_summary" in res_esg.json()

    # 6. Audit integrity endpoint
    res_audit = client.get(f"/api/reports/audit-logs/{org_id}/verify")
    assert res_audit.status_code == 200
    assert res_audit.json()["valid"] is True

    # 7. Dashboard HTML serving
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200
    assert "GreenCode Enterprise" in res_dash.text

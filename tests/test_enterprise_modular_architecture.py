"""Tests for the Enterprise Modular Architecture across all 8 subpackages."""

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app

@pytest.fixture(autouse=True)
def setup_database():
    init_db()

@pytest.fixture
def client():
    return TestClient(app)


def test_tenants_modular_routes(client):
    """Test /api/tenants/orgs endpoints."""
    res = client.post("/api/tenants/orgs", json={
        "name": "Acme Modular Cloud",
        "slug": "acme-mod-cloud",
        "tier": "enterprise",
        "sso_enabled": True,
    })
    assert res.status_code == 201
    data = res.json()
    org_id = data["id"]
    assert org_id is not None
    assert data["slug"] == "acme-mod-cloud"

    # Fetch tenant
    res_get = client.get(f"/api/tenants/orgs/{org_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Acme Modular Cloud"

    # List tenants
    res_list = client.get("/api/tenants/orgs")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_auth_modular_routes(client):
    """Test /api/auth/register and login."""
    res_reg = client.post("/api/auth/register", json={
        "email": "dev.admin@modular.greencode.dev",
        "username": "modularadmin",
        "password": "StrongPassword123!",
        "org_name": "Modular Org",
        "org_slug": "modular-org",
    })
    assert res_reg.status_code == 201
    data = res_reg.json()
    assert "tokens" in data
    assert "access_token" in data["tokens"]

    # Login
    res_login = client.post("/api/auth/login", json={
        "username_or_email": "modularadmin",
        "password": "StrongPassword123!",
    })
    assert res_login.status_code == 200
    assert "access_token" in res_login.json()["tokens"]


def test_audit_modular_routes(client):
    """Test /api/audit/scan on a sample file."""
    res_scan = client.post("/api/audit/scan", json={
        "path": "app/core/config.py",
        "commit_sha": "testsha123",
    })
    assert res_scan.status_code == 200
    data = res_scan.json()
    assert "green_score" in data
    assert "total_energy_joules" in data


def test_energy_modular_routes(client):
    """Test /api/energy/calculate and team budget routes."""
    res_calc = client.post("/api/energy/calculate", json={
        "duration_seconds": 1.5,
        "cpu_utilization_pct": 45.0,
        "memory_mb": 512.0,
        "cloud_instance": "c6g.xlarge",
    })
    assert res_calc.status_code == 200
    data = res_calc.json()
    assert data["energy_joules"] > 0
    assert data["cloud_profile_used"] == "c6g.xlarge"
    assert data["confidence_score"] > 0.8


def test_policies_modular_routes(client):
    """Test /api/policies/{org_id} and evaluate endpoint."""
    res_get = client.get("/api/policies/1")
    assert res_get.status_code == 200
    assert "max_regression_pct" in res_get.json()

    # Post policy
    res_save = client.post("/api/policies/org/1", json={
        "name": "Strict Zero-Carbon Policy",
        "max_regression_pct": 10.0,
        "warning_threshold_pct": 65.0,
        "breach_threshold_pct": 100.0,
    })
    assert res_save.status_code == 200
    assert res_save.json()["max_regression_pct"] == 10.0

    # Evaluate deployment: regression exceeds 10%
    res_eval = client.post("/api/policies/evaluate", json={
        "org_id": 1,
        "current_energy": 0.20,
        "baseline_energy": 0.10,  # 100% regression
        "team_budget_consumed": 50.0,
        "team_budget_total": 500.0,
    })
    assert res_eval.status_code == 200
    eval_data = res_eval.json()
    assert eval_data["decision"] == "BLOCK"
    assert eval_data["is_blocked"] is True


def test_kubernetes_modular_routes(client):
    """Test /api/kubernetes/evaluate-rollback."""
    res_k8s = client.post("/api/kubernetes/evaluate-rollback", json={
        "namespace": "prod-east",
        "deployment_name": "checkout-svc",
        "current_power_w": 350.0,
        "baseline_power_w": 200.0,
        "auto_trigger": True,
    })
    assert res_k8s.status_code == 200
    data = res_k8s.json()
    assert data["spike_pct"] >= 35.0
    assert data["verdict"] == "CRITICAL_SPIKE"
    assert data["rollback_triggered"] is True


def test_reports_modular_routes(client):
    """Test /api/reports/esg/1, HTML, and CSV export."""
    res_esg = client.get("/api/reports/esg/1")
    assert res_esg.status_code == 200
    assert "emissions_summary" in res_esg.json()

    res_html = client.get("/api/reports/esg/1/html")
    assert res_html.status_code == 200
    assert "<!DOCTYPE html>" in res_html.text

    res_csv = client.get("/api/reports/esg/1/csv")
    assert res_csv.status_code == 200
    assert "Report ID" in res_csv.text


def test_notifications_modular_routes(client):
    """Test /api/notifications/send endpoint."""
    res_notify = client.post("/api/notifications/send", json={
        "title": "Carbon Budget Overrun Warning",
        "message": "Team Payment API has crossed 90% monthly quota",
        "severity": "CRITICAL",
        "channel": "console",
    })
    assert res_notify.status_code == 200
    assert res_notify.json()["success"] is True


def test_pr_gate_modular_routes(client):
    """Test /api/pr-gate/compare endpoint."""
    res_pr = client.post("/api/pr-gate/compare", json={
        "base_scan": {"total_energy_joules": 0.05, "green_score": 92.0},
        "head_scan": {"total_energy_joules": 0.048, "green_score": 94.0},
        "max_regression_pct": 15.0,
    })
    assert res_pr.status_code == 200
    data = res_pr.json()
    assert data["verdict"] == "APPROVED"
    assert "🟢 PASSED - GREEN VERIFIED" in data["pr_markdown_comment"]


def test_admin_modular_routes(client):
    """Test /api/admin/health, settings, and audit-logs."""
    res_health = client.get("/api/admin/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "HEALTHY"

    res_settings = client.get("/api/admin/settings")
    assert res_settings.status_code == 200
    assert "enforce_policies" in res_settings.json()

    res_patch = client.patch("/api/admin/settings", json={"enforce_policies": False})
    assert res_patch.status_code == 200
    assert res_patch.json()["enforce_policies"] is False

    res_audit = client.get("/api/admin/audit-logs/1")
    assert res_audit.status_code == 200
    assert isinstance(res_audit.json(), list)

    res_verify = client.get("/api/admin/audit-logs/1/verify")
    assert res_verify.status_code == 200
    assert "valid" in res_verify.json()

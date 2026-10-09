"""Enterprise Authentication, RBAC & Multi-Tenant Isolation Test Suite.

Proves the enterprise control plane is no longer wide open:
  1. Anonymous callers receive 401.
  2. Callers lacking the required permission receive 403.
  3. A token for tenant A can never read or mutate tenant B (403).
  4. A platform superadmin may operate across every tenant.
  5. Canonical guards are the single source of truth (no core/auth drift).
"""

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.auth.jwt import create_tokens
from app.auth.roles import Role, Permission, has_permission


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def _auth(role, org_id=1):
    tokens = create_tokens(user_id=4242, org_id=org_id, role=role)
    return {"Authorization": "Bearer " + tokens["access_token"]}


def test_canonical_guard_is_single_source_of_truth():
    import app.core.dependencies as legacy
    import app.auth.dependencies as canonical
    assert legacy.get_current_actor is canonical.get_current_actor
    assert legacy.require_permission is canonical.require_permission
    assert legacy.get_tenant_actor is canonical.get_tenant_actor
    assert legacy.require_role is canonical.require_role


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/api/orgs/1", None),
        ("post", "/api/orgs", {"name": "X", "slug": "x", "tier": "free"}),
        ("get", "/api/tenants/orgs/1", None),
        ("get", "/api/policies/1", None),
        ("get", "/api/budgets/status/platform", None),
        ("post", "/api/kubernetes/evaluate-rollback", {"namespace": "prod", "deployment_name": "svc", "current_power_w": 200.0, "baseline_power_w": 150.0, "auto_trigger": True}),
        ("get", "/api/admin/settings", None),
        ("get", "/api/admin/audit-logs/1", None),
        ("get", "/api/admin/audit-logs/1/verify", None),
        ("post", "/api/audit/scan", {"path": "app/core/config.py"}),
    ],
)
def test_anonymous_access_is_denied(client, method, path, payload):
    res = client.request(method, path, json=payload)
    assert res.status_code == 401, method.upper() + " " + path + " -> " + str(res.status_code)


def test_admin_health_is_public_liveness_probe(client):
    res = client.get("/api/admin/health")
    assert res.status_code == 200
    assert res.json()["status"] == "HEALTHY"


def test_viewer_cannot_allocate_budget(client):
    res = client.post("/api/budgets/allocate", json={"org_id": 1, "team_id": "platform", "monthly_budget_kg": 100.0}, headers=_auth(Role.VIEWER.value))
    assert res.status_code == 403


def test_developer_cannot_trigger_kubernetes_rollback(client):
    res = client.post("/api/kubernetes/evaluate-rollback", json={"namespace": "prod", "deployment_name": "payments", "current_power_w": 300.0, "baseline_power_w": 180.0, "auto_trigger": True}, headers=_auth(Role.DEVELOPER.value))
    assert res.status_code == 403


def test_developer_cannot_update_admin_settings(client):
    res = client.patch("/api/admin/settings", json={"enforce_policies": False}, headers=_auth(Role.DEVELOPER.value))
    assert res.status_code == 403


def test_cross_tenant_org_read_is_denied(client):
    res = client.get("/api/orgs/999", headers=_auth(Role.ORG_ADMIN.value, org_id=1))
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


def test_cross_tenant_policy_evaluate_is_denied(client):
    res = client.post("/api/policies/evaluate", json={"org_id": 999, "current_energy": 1.4, "baseline_energy": 1.0, "team_budget_consumed": 200.0, "team_budget_total": 500.0}, headers=_auth(Role.ORG_ADMIN.value, org_id=1))
    assert res.status_code == 403


def test_cross_tenant_budget_status_is_denied(client):
    res = client.get("/api/budgets/status/platform", params={"org_id": 999}, headers=_auth(Role.ORG_ADMIN.value, org_id=1))
    assert res.status_code == 403


def test_superadmin_can_read_any_tenant(client):
    res = client.get("/api/orgs/999", headers=_auth(Role.SUPERADMIN.value, org_id=1))
    assert res.status_code in (200, 404)


def test_org_admin_can_read_admin_settings(client):
    res = client.get("/api/admin/settings", headers=_auth(Role.ORG_ADMIN.value, org_id=1))
    assert res.status_code == 200
    assert "enforce_policies" in res.json()

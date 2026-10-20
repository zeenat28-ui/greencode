"""Energy API Authorization & Tenant-Isolation Regression Tests.

The ``/api/energy/*`` surface used to be served by two overlapping routers
(``app.routers.energy_deployment`` and ``app.energy.routers``) with NO
authentication, NO RBAC and NO tenant isolation.  These tests lock in the
secure behaviour:

  1. Anonymous callers receive 401 on every energy endpoint.
  2. Callers lacking the required permission receive 403.
  3. An authorised caller succeeds.
  4. A token for tenant A can never touch tenant B (403).
  5. A platform superadmin may operate across tenants.
"""

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.auth.jwt import create_tokens
from app.auth.roles import Role


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def _auth(role, org_id=1):
    tokens = create_tokens(user_id=4242, org_id=org_id, role=role)
    return {"Authorization": "Bearer " + tokens["access_token"]}


# ---------------------------------------------------------------------------
# Route / method / body matrix
# ---------------------------------------------------------------------------

ENERGY_ROUTES = [
    ("get", "/api/energy/workloads", None),
    ("post", "/api/energy/workloads/baseline", {
        "namespace": "prod",
        "deployment_name": "payments",
        "baseline_power_w": 150.0,
    }),
    ("post", "/api/energy/policy", {
        "project_id": 1,
        "policy": {"max_energy_regression_pct": 10.0},
    }),
    ("post", "/api/energy/compare-baseline", {
        "project_id": 1,
        "current_metrics": {"energy_joules": 100.0, "green_score": 95.0, "sci_gco2e": 10.0},
        "baseline_metrics": {"energy_joules": 100.0},
        "grid_intensity": 380.0,
    }),
    ("post", "/api/energy/rollback", {
        "namespace": "prod",
        "deployment_name": "payments",
        "current_power_w": 200.0,
        "baseline_power_w": 150.0,
        "auto_trigger": False,
    }),
    ("get", "/api/energy/budgets", None),
    ("post", "/api/energy/budgets/allocate", {
        "team_id": "core-infra",
        "monthly_budget_kg": 250.0,
    }),
    ("post", "/api/energy/budgets/evaluate-pr", {
        "team_id": "core-infra",
        "additional_projected_kg_co2e": 12.5,
    }),
    ("post", "/api/energy/calculate", {
        "duration_seconds": 1.5,
        "cpu_utilization_pct": 45.0,
        "memory_mb": 512.0,
        "cloud_instance": "c6g.xlarge",
    }),
    ("get", "/api/energy/budgets/team/1/core-infra", None),
]


# ---------------------------------------------------------------------------
# 1. Anonymous access
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("method,path,payload", ENERGY_ROUTES)
def test_anonymous_energy_access_is_denied(client, method, path, payload):
    res = client.request(method, path, json=payload)
    assert res.status_code == 401, f"{method.upper()} {path} -> {res.status_code}"
    assert "WWW-Authenticate" in (res.headers or {})


def test_anonymous_energy_access_with_invalid_token_is_denied(client):
    res = client.get(
        "/api/energy/budgets",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# 2. Insufficient permissions
# ---------------------------------------------------------------------------

def test_viewer_cannot_allocate_energy_budget(client):
    res = client.post(
        "/api/energy/budgets/allocate",
        json={"team_id": "core-infra", "monthly_budget_kg": 100.0},
        headers=_auth(Role.VIEWER.value),
    )
    assert res.status_code == 403
    assert "budget:configure" in res.json()["detail"]


def test_developer_cannot_execute_energy_rollback(client):
    res = client.post(
        "/api/energy/rollback",
        json={
            "namespace": "prod",
            "deployment_name": "payments",
            "current_power_w": 300.0,
            "baseline_power_w": 180.0,
            "auto_trigger": False,
        },
        headers=_auth(Role.DEVELOPER.value),
    )
    assert res.status_code == 403
    assert "deploy:rollback" in res.json()["detail"]


def test_developer_cannot_override_energy_policy(client):
    res = client.post(
        "/api/energy/policy",
        json={"project_id": 1, "policy": {"max_energy_regression_pct": 1.0}},
        headers=_auth(Role.DEVELOPER.value),
    )
    assert res.status_code == 403
    assert "policy:override" in res.json()["detail"]


def test_developer_cannot_set_workload_baseline(client):
    res = client.post(
        "/api/energy/workloads/baseline",
        json={"namespace": "prod", "deployment_name": "payments", "baseline_power_w": 150.0},
        headers=_auth(Role.DEVELOPER.value),
    )
    assert res.status_code == 403
    assert "deploy:approve" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 3. Authorized access
# ---------------------------------------------------------------------------

def test_viewer_can_read_energy_budgets(client):
    res = client.get("/api/energy/budgets", headers=_auth(Role.VIEWER.value, org_id=1))
    assert res.status_code == 200
    body = res.json()
    assert "budgets" in body
    assert body["org_id"] == 1


def test_developer_can_calculate_energy(client):
    res = client.post(
        "/api/energy/calculate",
        json={
            "duration_seconds": 1.5,
            "cpu_utilization_pct": 45.0,
            "memory_mb": 512.0,
            "cloud_instance": "c6g.xlarge",
        },
        headers=_auth(Role.DEVELOPER.value),
    )
    assert res.status_code == 200
    assert res.json()["energy_joules"] > 0


def test_org_admin_can_allocate_budget_in_own_tenant(client):
    res = client.post(
        "/api/energy/budgets/allocate",
        json={"team_id": "core-infra", "monthly_budget_kg": 250.0},
        headers=_auth(Role.ORG_ADMIN.value, org_id=1),
    )
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_energy_budget_defaults_to_authenticated_tenant(client):
    """A client that omits ``org_id`` must land in its own tenant."""
    res = client.get("/api/energy/budgets", headers=_auth(Role.VIEWER.value, org_id=7))
    assert res.status_code == 200
    assert res.json()["org_id"] == 7


# ---------------------------------------------------------------------------
# 4. Cross-tenant rejection
# ---------------------------------------------------------------------------

def test_cross_tenant_budget_list_is_denied(client):
    res = client.get(
        "/api/energy/budgets",
        params={"org_id": 999},
        headers=_auth(Role.ORG_ADMIN.value, org_id=1),
    )
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


def test_cross_tenant_budget_allocation_is_denied(client):
    res = client.post(
        "/api/energy/budgets/allocate",
        json={"org_id": 999, "team_id": "core-infra", "monthly_budget_kg": 250.0},
        headers=_auth(Role.ORG_ADMIN.value, org_id=1),
    )
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


def test_cross_tenant_pr_evaluation_is_denied(client):
    res = client.post(
        "/api/energy/budgets/evaluate-pr",
        json={"org_id": 999, "team_id": "core-infra", "additional_projected_kg_co2e": 5.0},
        headers=_auth(Role.ORG_ADMIN.value, org_id=1),
    )
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


def test_cross_tenant_rollback_is_denied(client):
    res = client.post(
        "/api/energy/rollback",
        json={
            "org_id": 999,
            "namespace": "prod",
            "deployment_name": "payments",
            "current_power_w": 200.0,
            "baseline_power_w": 150.0,
            "auto_trigger": False,
        },
        headers=_auth(Role.ORG_ADMIN.value, org_id=1),
    )
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


def test_cross_tenant_policy_override_is_denied(client):
    """``policy:override`` is a superadmin-only permission.

    A tenant ``org_admin`` is refused on the permission check before the
    tenant boundary is even reached - it must never be able to write another
    tenant's policy, nor its own.
    """
    res = client.post(
        "/api/energy/policy",
        json={"project_id": 1, "org_id": 999, "policy": {"max_energy_regression_pct": 1.0}},
        headers=_auth(Role.ORG_ADMIN.value, org_id=1),
    )
    assert res.status_code == 403
    assert "policy:override" in res.json()["detail"]


def test_superadmin_can_set_energy_policy(client):
    res = client.post(
        "/api/energy/policy",
        json={"project_id": 1, "org_id": 999, "policy": {"max_energy_regression_pct": 12.0}},
        headers=_auth(Role.SUPERADMIN.value, org_id=1),
    )
    assert res.status_code == 200
    assert res.json()["max_energy_regression_pct"] == 12.0


def test_cross_tenant_team_budget_status_is_denied(client):
    res = client.get(
        "/api/energy/budgets/team/999/core-infra",
        headers=_auth(Role.VIEWER.value, org_id=1),
    )
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


# ---------------------------------------------------------------------------
# 5. Superadmin cross-tenant access
# ---------------------------------------------------------------------------

def test_superadmin_can_read_cross_tenant_budgets(client):
    res = client.get(
        "/api/energy/budgets",
        params={"org_id": 999},
        headers=_auth(Role.SUPERADMIN.value, org_id=1),
    )
    assert res.status_code == 200
    assert res.json()["org_id"] == 999


def test_superadmin_can_allocate_cross_tenant_budget(client):
    res = client.post(
        "/api/energy/budgets/allocate",
        json={"org_id": 999, "team_id": "core-infra", "monthly_budget_kg": 250.0},
        headers=_auth(Role.SUPERADMIN.value, org_id=1),
    )
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_superadmin_can_read_cross_tenant_team_budget(client):
    res = client.get(
        "/api/energy/budgets/team/999/core-infra",
        headers=_auth(Role.SUPERADMIN.value, org_id=1),
    )
    assert res.status_code == 200
    assert res.json()["org_id"] == 999



"""Frontend/backend API contract regression tests.

These tests lock in the contracts that the React dashboard and the static
enterprise dashboard depend on.  They exist because several of these
endpoints were previously called with the wrong HTTP verb, the wrong
request-body field names, or without an ``Authorization`` header (the
access token is only ever held in memory by the frontend).

Covered contracts:
  1. ``GET /api/enterprise/organizations`` returns the tenant list shape.
  2. ``POST /api/tenants/switch`` returns new tokens for the target org.
  3. ``GET /api/reports/audit-logs/{org_id}`` returns a bare JSON array.
  4. ``GET /api/reports/audit-logs/{org_id}/verify`` returns
     ``records_verified`` (not ``checked_records``).
  5. ``POST /api/energy/budgets/evaluate-pr`` accepts ``team_id`` and
     ``additional_projected_kg_co2e`` and returns a ``verdict``.
  6. ``GET /api/auth/me`` returns ``{authenticated, user}``.
"""

import pytest
from fastapi.testclient import TestClient

from app.database import init_db, create_user, create_organization
from app.main import app
from app.auth.jwt import create_tokens
from app.auth.roles import Role


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def tenant_user():
    """Create a real user + org so token-backed routes can resolve the user.

    Session-scoped on purpose: ``create_user`` refuses to create a duplicate
    email, and ``create_organization`` is idempotent per slug, so a
    function-scoped fixture would raise "An account with this email address
    already exists" on the second test that requested it.
    """
    init_db()
    org = create_organization(name="Contract Test Org", slug="contract-test-org")
    user = create_user(
        email="contract-test-user@greencode.io",
        username="contract_test_user",
        password="P@ssw0rd2026!",
        full_name="Contract Test User",
        role=Role.SUPERADMIN.value,
        auto_verify=True,
        org_id=org["id"],
    )
    return user, org


def _headers(user_id: int = 1, org_id: int = 1, role: str = Role.SUPERADMIN.value):
    tokens = create_tokens(user_id=user_id, org_id=org_id, role=role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_organizations_list_contract(client, tenant_user):
    """`GET /api/enterprise/organizations` must list orgs, not 500."""
    user, org = tenant_user
    res = client.get("/api/enterprise/organizations", headers=_headers(user_id=user["id"], org_id=org["id"]))
    assert res.status_code == 200, res.text
    body = res.json()
    assert "organizations" in body
    assert isinstance(body["organizations"], list)
    assert "current_org_id" in body
    assert any(o["id"] == org["id"] for o in body["organizations"])


def test_organizations_list_requires_authentication(client):
    """The org listing is a protected route."""
    assert client.get("/api/enterprise/organizations").status_code == 401


def test_organizations_me_contract(client, tenant_user):
    """`GET /api/enterprise/organizations/me` returns is_tenant + organization."""
    user, org = tenant_user
    res = client.get("/api/enterprise/organizations/me", headers=_headers(user_id=user["id"], org_id=org["id"]))
    assert res.status_code == 200, res.text
    body = res.json()
    assert "is_tenant" in body
    assert "organization" in body


def test_auth_me_contract(client, tenant_user):
    """`GET /api/auth/me` returns {authenticated, user} as the frontend expects."""
    user, org = tenant_user
    res = client.get("/api/auth/me", headers=_headers(user_id=user["id"], org_id=org["id"]))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["authenticated"] is True
    assert body["user"]["id"] == user["id"]
    assert "email" in body["user"]


def test_switch_tenant_returns_new_tokens(client, tenant_user):
    """`POST /api/tenants/switch` must not 500 and must return fresh tokens."""
    user, org = tenant_user
    res = client.post(
        "/api/tenants/switch",
        json={"org_id": org["id"]},
        headers=_headers(user_id=user["id"], org_id=org["id"]),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("success") is True
    assert "access_token" in body
    assert "refresh_token" in body


def test_switch_tenant_requires_org_id(client, tenant_user):
    """A missing org_id is a 400, not a 500."""
    user, org = tenant_user
    res = client.post(
        "/api/tenants/switch",
        json={"org_id": 0},
        headers=_headers(user_id=user["id"], org_id=org["id"]),
    )
    assert res.status_code == 400


def test_audit_log_trail_returns_bare_array(client):
    """The audit trail endpoint returns a bare JSON array (not {entries: []})."""
    res = client.get("/api/reports/audit-logs/1?limit=5")
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body, list)
    if body:
        entry = body[0]
        # The frontend renders these backend field names.
        for field in ("action", "resource_type", "resource_id", "created_at"):
            assert field in entry, f"missing backend field: {field}"


def test_audit_log_verification_uses_get_and_records_verified(client):
    """Verification is a GET and reports `records_verified`."""
    res = client.get("/api/reports/audit-logs/1/verify")
    assert res.status_code == 200, res.text
    body = res.json()
    assert "records_verified" in body
    assert "checked_records" not in body
    assert "valid" in body
    assert "status" in body


def test_evaluate_pr_accepts_frontend_payload(client):
    """`evaluate-pr` accepts the frontend's team_id / additional_projected_kg_co2e."""
    res = client.post(
        "/api/energy/budgets/evaluate-pr",
        json={
            "org_id": 1,
            "team_id": "core-infra",
            "additional_projected_kg_co2e": 12.5,
        },
        headers=_headers(),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert "verdict" in body
    # The backend emits PASSED / WARNING / BLOCKED (see BudgetService.evaluate_pr_impact).
    assert body["verdict"] in {"PASSED", "WARNING", "BLOCKED"}


def test_evaluate_pr_rejects_negative_projection(client):
    """`additional_projected_kg_co2e` is constrained to be >= 0."""
    res = client.post(
        "/api/energy/budgets/evaluate-pr",
        json={
            "org_id": 1,
            "team_id": "core-infra",
            "additional_projected_kg_co2e": -5.0,
        },
        headers=_headers(),
    )
    assert res.status_code == 422


def test_energy_budgets_contract(client):
    """`GET /api/energy/budgets` returns the team status plus the budget list."""
    res = client.get("/api/energy/budgets", headers=_headers())
    assert res.status_code == 200, res.text
    body = res.json()
    assert "budgets" in body
    assert isinstance(body["budgets"], list)
    for field in ("monthly_budget_kg", "current_consumed_kg", "consumption_pct", "alert_level"):
        assert field in body, f"missing team-status field: {field}"

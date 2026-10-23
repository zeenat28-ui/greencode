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
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlparse
from fastapi.testclient import TestClient

from app.database import init_db, create_user, create_organization
from app.main import app
from app.auth.oauth import OAuthManager
from app.auth.jwt import create_tokens
from app.auth.roles import Role
from app.services.budget_service import BudgetService


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

def test_github_oauth_connection_requires_authenticated_greencode_user(client):
    response = client.post(
        "/api/auth/github/connect",
        json={"code": "github-code", "redirect_uri": "http://localhost:5173/login"},
    )
    assert response.status_code == 401


def test_github_oauth_connection_returns_repo_access_without_replacing_platform_session(
    client, tenant_user, monkeypatch
):
    user, org = tenant_user
    exchange = AsyncMock(return_value={
        "access_token": "github-session-token",
        "username": "connected-developer",
        "avatar_url": "https://avatars.githubusercontent.com/u/42",
    })
    monkeypatch.setattr(OAuthManager, "exchange_github_code", exchange)

    response = client.post(
        "/api/auth/github/connect",
        json={"code": "github-code", "redirect_uri": "http://localhost:5173/login"},
        headers=_headers(user_id=user["id"], org_id=org["id"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "success": True,
        "github_token": "github-session-token",
        "github_user": {
            "login": "connected-developer",
            "avatar_url": "https://avatars.githubusercontent.com/u/42",
        },
    }
    exchange.assert_awaited_once_with("github-code", "http://localhost:5173/login")


def test_google_authorize_requires_state(client):
    response = client.get("/api/auth/google/authorize")

    assert response.status_code == 422


def test_google_authorize_encodes_state_and_redirect_without_forced_consent(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-google-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
    state = "unguessable-google-state-value"
    redirect_uri = "http://localhost:5173/login?provider=google"

    response = client.get(
        "/api/auth/google/authorize",
        params={"redirect_uri": redirect_uri, "state": state},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    query = parse_qs(urlparse(payload["auth_url"]).query)
    assert payload["configured"] is True
    assert query["state"] == [state]
    assert query["redirect_uri"] == [redirect_uri]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert "prompt" not in query


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
    res = client.get("/api/reports/audit-logs/1?limit=5", headers=_headers())
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
    res = client.get("/api/reports/audit-logs/1/verify", headers=_headers())
    assert res.status_code == 200, res.text
    body = res.json()
    assert "records_verified" in body
    assert "checked_records" not in body
    assert "valid" in body
    assert "status" in body


def test_report_endpoints_require_authentication_and_tenant_scope(client):
    """Organization reports reject anonymous and cross-tenant requests."""
    assert client.get("/api/reports/esg/1").status_code == 401
    assert client.get("/api/reports/audit-logs/1").status_code == 401
    assert client.get(
        "/api/reports/esg/2",
        headers=_headers(org_id=1, role=Role.AUDITOR.value),
    ).status_code == 403


def test_billing_usage_defaults_to_authenticated_organization(client, tenant_user):
    """The usage endpoint derives the tenant from the bearer session, not org 1."""
    user, org = tenant_user
    response = client.get(
        "/api/billing/usage",
        headers=_headers(user_id=user["id"], org_id=org["id"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["org_id"] == org["id"]


def test_license_activation_requires_authenticated_tenant_admin(client):
    response = client.post(
        "/api/billing/license/activate",
        json={"org_id": 1, "license_key": "GC-LIC-invalid"},
    )
    assert response.status_code == 401

    tokens = create_tokens(user_id=1, org_id=1, role=Role.VIEWER.value)
    response = client.post(
        "/api/billing/license/activate",
        json={"org_id": 1, "license_key": "GC-LIC-invalid"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403


def test_evaluate_pr_accepts_frontend_payload(client):
    """`evaluate-pr` accepts the frontend's team_id / additional_projected_kg_co2e."""
    BudgetService.allocate_budget(org_id=1, team_id="core-infra", monthly_budget_kg=500.0)
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
    BudgetService.allocate_budget(org_id=1, team_id="core-infra", monthly_budget_kg=500.0)
    res = client.get("/api/energy/budgets", headers=_headers())
    assert res.status_code == 200, res.text
    body = res.json()
    assert "budgets" in body
    assert isinstance(body["budgets"], list)
    for field in ("monthly_budget_kg", "current_consumed_kg", "consumption_pct", "alert_level"):
        assert field in body, f"missing team-status field: {field}"


def test_refactor_rejects_unsupported_network_snippet(client, tenant_user):
    """A network finding without a supported loop rewrite is not presented as a patch."""
    user, org = tenant_user
    response = client.post(
        "/api/refactor",
        json={
            "snippet": "try:\n    await websocket.send_text(message)\nexcept Exception:\n    pass",
            "violation_type": "UNCACHED_NETWORK",
            "language": "python",
        },
        headers=_headers(user_id=user["id"], org_id=org["id"]),
    )

    assert response.status_code == 422
    assert "cannot be safely rewritten" in response.json()["detail"]


def test_refactor_reuses_session_for_supported_request_loop(client, tenant_user, monkeypatch):
    """A complete requests loop still receives the deterministic connection-pooling rewrite."""
    user, org = tenant_user
    monkeypatch.setenv("GREENCODE_LLM_PROVIDER", "none")
    response = client.post(
        "/api/refactor",
        json={
            "snippet": "for item in items:\n    requests.get(item.url)",
            "violation_type": "UNCACHED_NETWORK",
            "language": "python",
        },
        headers=_headers(user_id=user["id"], org_id=org["id"]),
    )

    assert response.status_code == 200, response.text
    patch = response.json()["refactored_code"]
    assert "session = requests.Session()" in patch
    assert "session.get(item.url)" in patch
    assert "requests.get(item.url)" not in patch


def test_refactor_rejects_generic_nested_loop_patch(client, tenant_user):
    """A generic loop-depth finding must not produce unrelated placeholder code."""
    user, org = tenant_user
    response = client.post(
        "/api/refactor",
        json={
            "snippet": "for (int c = 0; c < 3; ++c) { value += pixels[c]; }",
            "violation_type": "NESTED_LOOPS_DEPTH_3+",
            "language": "cpp",
        },
        headers=_headers(user_id=user["id"], org_id=org["id"]),
    )

    assert response.status_code == 422
    assert "Loop depth alone" in response.json()["detail"]


def test_scope_inventory_matches_cloud_carbon_response_contract(client):
    response = client.post(
        "/api/scope/inventory",
        json={
            "energy_joules": 360000,
            "duration_seconds": 3600,
            "grid_intensity_gco2_per_kwh": 380,
            "runs_per_year": 50000,
            "team_size": 12,
            "dev_hours": 160,
            "cloud_provider": "aws",
            "vcpu_count": 8,
            "memory_gb": 32,
            "data_transfer_gb": 5.0,
            "renewable_rec_pct": 0,
        },
    )

    assert response.status_code == 200, response.text
    report = response.json()
    assert isinstance(report["scope_1"]["direct_emissions_kgco2e"], (int, float))
    assert isinstance(report["scope_2"]["location_based_kgco2e"], (int, float))
    assert isinstance(report["scope_2"]["total_energy_kwh_annual"], (int, float))
    assert isinstance(report["scope_2"]["pue"], (int, float))
    assert isinstance(report["scope_3"]["total_scope3_kgco2e_annual"], (int, float))
    assert isinstance(report["scope_3"]["embodied_hardware_gco2e_annual"], (int, float))
    assert isinstance(report["total_carbon_kgco2e_annual"], (int, float))


def test_ml_token_projection_matches_cloud_carbon_response_contract(client):
    response = client.post(
        "/api/ml/tokens",
        json={
            "parameter_count_b": 7,
            "token_count": 2048,
            "hardware": "h100",
            "grid_intensity_gco2_per_kwh": 200,
            "runs_per_year": 1_000_000,
        },
    )

    assert response.status_code == 200, response.text
    result = response.json()
    for field in (
        "energy_joules",
        "energy_kwh",
        "carbon_gco2e",
        "joules_per_token",
        "gco2e_per_1k_tokens",
        "annual_cost_usd_at_scale",
        "recommendation",
    ):
        assert field in result, f"missing model-token field: {field}"


def test_ml_audit_matches_cloud_carbon_response_contract(client):
    response = client.post(
        "/api/ml/audit",
        json={
            "source_code": (
                "import torch\n"
                "model = torch.nn.Linear(4, 2)\n"
                "model.eval()\n"
                "def predict(values):\n"
                "    return model(values).cpu().numpy()\n"
            ),
            "file_path": "model.py",
        },
    )

    assert response.status_code == 200, response.text
    result = response.json()
    for field in ("file_or_repo", "ml_green_score", "violations_count", "violations", "frameworks_detected"):
        assert field in result, f"missing ML audit field: {field}"
    if result["violations"]:
        violation = result["violations"][0]
        for field in ("rule", "severity", "line", "deduction", "description", "remediation", "code_snippet"):
            assert field in violation, f"missing ML violation field: {field}"


def test_unallocated_team_has_no_default_budget(client):
    """Reading budget status must not invent or persist an unconfigured quota."""
    org_id = 987654321
    res = client.get(
        "/api/energy/budgets",
        params={"org_id": org_id, "team_id": "unallocated-team", "period": "2099-01"},
        headers=_headers(org_id=1),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["org_id"] == org_id
    assert body["team_status"] is None
    assert body["budgets"] == []

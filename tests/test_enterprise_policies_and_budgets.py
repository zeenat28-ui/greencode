"""Unit tests for Enterprise Policy Engine, Carbon Budget Manager, and PR Comments."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db
from app.services.policy_service import PolicyService
from app.budgets import CarbonBudgetManager
from app.github_integration.pr_comment import format_pr_sticky_comment, GATE_MARKER


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


@pytest.fixture
def client():
    return TestClient(app)


def test_policy_engine_evaluation_rules():
    """Verify regression limits (>25%) and budget thresholds (70%, 90%, 100%)."""
    org_id = 1

    # 1. Normal run within tolerance
    eval_ok = PolicyService.evaluate_deployment_rules(
        org_id=org_id,
        current_energy=1.1,
        baseline_energy=1.0,  # +10% regression < 25%
        team_budget_consumed=200.0,
        team_budget_total=500.0,  # 40% < 70%
    )
    assert eval_ok["decision"] == "PASS"
    assert eval_ok["is_blocked"] is False

    # 2. Critical energy regression (>25% spike) -> BLOCK
    eval_spike = PolicyService.evaluate_deployment_rules(
        org_id=org_id,
        current_energy=1.4,
        baseline_energy=1.0,  # +40% regression > 25%
        team_budget_consumed=200.0,
        team_budget_total=500.0,
    )
    assert eval_spike["decision"] == "BLOCK"
    assert eval_spike["is_blocked"] is True
    assert len(eval_spike["violations"]) > 0

    # 3. Budget warning (>70% consumed) -> WARN
    eval_warn = PolicyService.evaluate_deployment_rules(
        org_id=org_id,
        current_energy=1.05,
        baseline_energy=1.0,  # +5% regression
        team_budget_consumed=380.0,
        team_budget_total=500.0,  # 76% consumed
    )
    assert eval_warn["decision"] == "WARN"
    assert eval_warn["is_blocked"] is False

    # 4. Budget breach (>=100% consumed) -> BLOCK
    eval_breach = PolicyService.evaluate_deployment_rules(
        org_id=org_id,
        current_energy=1.02,
        baseline_energy=1.0,
        team_budget_consumed=520.0,
        team_budget_total=500.0,  # 104% consumed
    )
    assert eval_breach["decision"] == "BLOCK"
    assert eval_breach["is_blocked"] is True


def test_carbon_budget_manager_forecast():
    """Verify daily burn velocity and forecasted overrun calculations."""
    forecast = CarbonBudgetManager.calculate_forecast(
        consumed_kg=150.0,
        budget_kg=200.0,
        year=2026,
        month=10,
        day=15,  # 15 days elapsed, burn rate = 10 kg/day
    )
    assert forecast["daily_burn_kg"] == 10.0
    # 31 days in October -> projected 310 kg > 200 kg budget
    assert forecast["projected_month_end_kg"] == 310.0
    assert forecast["will_overrun"] is True
    assert forecast["projected_overrun_kg"] == 110.0


def test_pr_sticky_comment_formatting():
    """Verify PR sticky comment generates valid Markdown and gate markers."""
    diff_data = {
        "verdict": "BLOCKED",
        "is_blocked": True,
        "energy_delta_pct": 34.2,
        "annual_cost_delta_usd": 6156.0,
        "annual_carbon_delta_kg": 1436.4,
        "base_green_score": 92.0,
        "head_green_score": 78.0,
    }
    comment = format_pr_sticky_comment(diff_data, repo_slug="acme/payments-api", pr_number=1042)
    assert GATE_MARKER in comment
    assert "FAILED - MERGE BLOCKED" in comment
    assert "acme/payments-api#1042" in comment
    assert "+34.20%" in comment
    assert "$6,156.00" in comment


def test_policies_rest_endpoints(client):
    """Verify policy management and live rule evaluation API endpoints."""
    # 1. Save policy
    res_save = client.post("/api/policies", json={
        "org_id": 1,
        "name": "Strict Zero-Regression Policy",
        "max_regression_pct": 10.0,
        "warning_threshold_pct": 75.0,
    })
    assert res_save.status_code == 200
    assert res_save.json()["max_regression_pct"] == 10.0

    # 2. Get policy
    res_get = client.get("/api/policies/1")
    assert res_get.status_code == 200
    assert res_get.json()["max_regression_pct"] == 10.0

    # 3. Evaluate rules endpoint
    res_eval = client.post("/api/policies/evaluate", json={
        "org_id": 1,
        "current_energy": 1.25,
        "baseline_energy": 1.0,  # 25% > 10% limit
        "team_budget_consumed": 100.0,
        "team_budget_total": 500.0,
    })
    assert res_eval.status_code == 200
    assert res_eval.json()["decision"] == "BLOCK"


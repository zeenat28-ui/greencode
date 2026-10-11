"""Unit and integration tests for app/amazon_service.py and app/routers/amazon.py."""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app import amazon_service
from app.main import app


class FakeSTSClient:
    def __init__(self, account_id: str = "123456789012", caller_account_id: str | None = None):
        self.account_id = account_id
        self.caller_account_id = caller_account_id or account_id
        self.calls = []

    def assume_role(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "Credentials": {
                "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
                "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "SessionToken": "AQoDYXdzEJr1EXAMPLETOKEN",
                "Expiration": datetime(2026, 10, 11, 20, 0, 0, tzinfo=timezone.utc),
            },
            "AssumedRoleUser": {
                "AssumedRoleId": "AROAEXAMPLEID:greencode",
                "Arn": f"arn:aws:sts::{self.account_id}:assumed-role/GreenCodeAuditor/session",
            },
        }

    def get_caller_identity(self):
        return {
            "UserId": "AROAEXAMPLEID:greencode",
            "Account": self.caller_account_id,
            "Arn": f"arn:aws:sts::{self.caller_account_id}:assumed-role/GreenCodeAuditor/session",
        }


class FakeBudgetsClient:
    def __init__(self, actual_usd: float = 136.0, forecast_usd: float = 200.0):
        self.actual_usd = actual_usd
        self.forecast_usd = forecast_usd
        self.calls = []

    def describe_budgets(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "Budgets": [
                {
                    "BudgetName": "greencode-monthly",
                    "CalculatedSpend": {
                        "ActualSpend": {"Amount": str(self.actual_usd), "Unit": "USD"},
                        "ForecastedSpend": {"Amount": str(self.forecast_usd), "Unit": "USD"},
                    },
                }
            ]
        }


def test_ember_2024_fallback_table_and_grid_zone_mapping(monkeypatch):
    # Ensure offline deterministic path resolves Ember 2024 cited values
    monkeypatch.setattr(
        amazon_service.carbon_intensity,
        "resolve_carbon_intensity",
        lambda zone, use_cache=True: type("Obj", (), {"is_live": False, "carbon_intensity": 0.0})(),
    )

    it = amazon_service.get_region_carbon_intensity("eu-south-1")
    assert it["grid_zone"] == "IT"
    assert abs(it["carbon_intensity"] - 281.4) < 1e-3
    assert it["source"] == "ember_2024_reference_table"
    assert "Ember Yearly Electricity Data 2024" in it["citation"]

    ca = amazon_service.get_region_carbon_intensity("ca-central-1")
    assert ca["grid_zone"] == "CA-QC"
    assert abs(ca["carbon_intensity"] - 185.35) < 1e-3

    us = amazon_service.get_region_carbon_intensity("us-east-1")
    assert us["grid_zone"] == "US-MIDA-PJM"
    assert abs(us["carbon_intensity"] - 383.78) < 1e-3

    se = amazon_service.get_region_carbon_intensity("eu-north-1")
    assert se["grid_zone"] == "SE"
    assert abs(se["carbon_intensity"] - 34.91) < 1e-3


def test_electricity_maps_uses_mapped_grid_zone_and_timeout(monkeypatch):
    captured = {}

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"carbonIntensity": 312.5}

    def fake_get(url, params=None, headers=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return FakeResp()

    monkeypatch.setattr(amazon_service.requests, "get", fake_get)
    res = amazon_service.get_region_carbon_intensity("eu-central-1", api_key="em-live-key")
    assert res["tier"] == "live"
    assert res["carbon_intensity"] == 312.5
    assert captured["params"] == {"zone": "DE"}  # Mapped grid zone, never raw 'eu-central-1'
    assert captured["timeout"] == 6.0


def test_account_id_and_role_arn_validation():
    # Invalid account ID
    with pytest.raises(ValueError, match="12 digits"):
        amazon_service.validate_account_and_role_arn("12345", "arn:aws:iam::123456789012:role/GreenCode")

    # Malformed Role ARN
    with pytest.raises(ValueError, match="Invalid IAM Role ARN"):
        amazon_service.validate_account_and_role_arn("123456789012", "not-an-arn")

    # Account ID in ARN does not match account_id parameter
    with pytest.raises(ValueError, match="Account ID mismatch"):
        amazon_service.validate_account_and_role_arn(
            "123456789012",
            "arn:aws:iam::999999999999:role/GreenCodeAuditor",
        )

    # STS get_caller_identity mismatch raises AWSSTSError
    bad_sts = FakeSTSClient(account_id="123456789012", caller_account_id="999999999999")
    with pytest.raises(amazon_service.AWSSTSError) as exc_info:
        amazon_service.assume_role(
            account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/GreenCodeAuditor",
            sts_client=bad_sts,
        )
    assert exc_info.value.error_code == "CALLER_IDENTITY_MISMATCH"


def test_link_list_and_delete_aws_account_no_credential_leak():
    sts = FakeSTSClient(account_id="123456789012")
    res = amazon_service.link_aws_account(
        account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/GreenCodeAuditor",
        region="us-east-1",
        account_name="Production FinOps Account",
        external_id="ext-123",
        org_id=1,
        sts_client=sts,
    )
    assert res["status"] == "LINKED"
    assert res["account_id"] == "123456789012"
    assert res["sts_session_verified"] is True
    # Ensure temporary STS credentials are NEVER leaked in the response
    assert "access_key_id" not in res
    assert "secret_access_key" not in res
    assert "session_token" not in res

    accounts = amazon_service.list_linked_accounts(org_id=1)
    assert any(a["account_id"] == "123456789012" for a in accounts)

    # Unique STS session name generated per call
    assert sts.calls[0]["RoleSessionName"].startswith("greencode-auditor-")
    assert sts.calls[0]["ExternalId"] == "ext-123"


def test_cross_account_cost_and_calibrated_carbon_attribution(monkeypatch):
    monkeypatch.setattr(
        amazon_service.carbon_intensity,
        "resolve_carbon_intensity",
        lambda zone, use_cache=True: type("Obj", (), {"is_live": False, "carbon_intensity": 0.0})(),
    )

    sts = FakeSTSClient(account_id="123456789012")
    # $136.00 spend = 1,000 hours of c6g.xlarge ($0.136/hr)
    budgets = FakeBudgetsClient(actual_usd=136.0, forecast_usd=180.0)

    data = amazon_service.get_aws_cost_carbon_data(
        region="us-east-1",
        account_id="123456789012",
        sts_client=sts,
        budgets_client=budgets,
    )
    now_mtd_start = datetime.now(timezone.utc).strftime("%Y-%m-01")
    assert data["period_start"] == now_mtd_start
    assert data["cost_usd"] == 136.0
    assert data["estimated_energy_kwh"] > 0.0
    assert data["estimated_co2e_kg"] > 0.0
    # Verify physical relationship: estimated_co2e_kg == estimated_energy_kwh * (383.78 / 1000)
    expected_co2 = round(data["estimated_energy_kwh"] * (383.78 / 1000.0), 4)
    assert abs(data["estimated_co2e_kg"] - expected_co2) < 1e-3

    # Clean up linked account
    assert amazon_service.delete_aws_account("123456789012", org_id=1) is True


def test_amazon_router_endpoints():
    client = TestClient(app)

    r_reg = client.get("/api/aws/regions")
    assert r_reg.status_code == 200
    body = r_reg.json()
    assert "us-east-1" in body["regions"]
    assert body["region_to_grid_zone"]["eu-south-1"] == "IT"

    r_ci = client.get("/api/aws/regions/eu-south-1/carbon-intensity")
    assert r_ci.status_code == 200
    assert r_ci.json()["grid_zone"] == "IT"


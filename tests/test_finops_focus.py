"""Tests for FinOps Foundation FOCUS 1.4 Cloud Billing & Carbon Reconciliation Engine."""

from fastapi.testclient import TestClient

from app.finops_focus import reconcile_focus_billing
from app.main import app

client = TestClient(app)


def test_focus_reconciliation_json_and_csv():
    res = reconcile_focus_billing()
    assert res["specification"] == "FinOps Foundation FOCUS 1.4"
    assert res["line_items_evaluated"] == 3
    summary = res["summary"]
    assert summary["total_effective_cost_usd"] > 0
    assert summary["total_energy_kwh"] > 0
    assert summary["total_carbon_kg_co2e"] > 0
    assert summary["identified_monthly_usd_savings"] > 0

    csv_payload = (
        "ProviderName,ServiceName,ResourceId,ResourceType,RegionId,ConsumedQuantity,BilledCost,EffectiveCost\n"
        "AWS,AmazonEC2,i-99999,m5.2xlarge,us-east-1,730,275.00,260.00\n"
    )
    csv_res = reconcile_focus_billing(csv_text=csv_payload)
    assert csv_res["line_items_evaluated"] == 1
    item = csv_res["reconciled_items"][0]
    assert item["resource_type"] == "m5.2xlarge"
    assert item["potential_monthly_usd_savings"] == 52.0
    assert len(item["recommendations"]) == 2


def test_focus_http_endpoints():
    r_sample = client.get("/api/billing/focus/sample-report")
    assert r_sample.status_code == 200
    assert r_sample.json()["line_items_evaluated"] == 3

    r_post = client.post(
        "/api/billing/focus/reconcile",
        json={
            "rows": [
                {
                    "ProviderName": "AWS",
                    "ServiceName": "AmazonEC2",
                    "ResourceId": "i-graviton-1",
                    "ResourceType": "c7g.large",
                    "RegionId": "eu-north-1",
                    "ConsumedQuantity": 730,
                    "BilledCost": 54.0,
                    "EffectiveCost": 50.0,
                }
            ]
        },
    )
    assert r_post.status_code == 200
    body = r_post.json()
    assert body["line_items_evaluated"] == 1
    assert body["reconciled_items"][0]["grid_zone"] == "SE"

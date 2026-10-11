"""Tests for the Extensible Plugin & Signed Webhook Architecture (app/plugins.py)."""

from fastapi.testclient import TestClient

from app.main import app
from app.plugins import PluginRegistry

client = TestClient(app)


def test_plugin_registry_hooks_and_webhook_signing():
    reg = PluginRegistry()
    cat = reg.list_catalog()
    assert cat["total_plugins"] >= 4

    received = []
    reg.register_hook("custom-hook", "audit.completed", lambda env: received.append(env["event"]))
    reg.register_webhook_sink(
        "datadog-finops-sink",
        "https://webhooks.example.com/greencode",
        events=["audit.completed"],
        secret="top-secret-key",
    )

    out = reg.dispatch_event("audit.completed", {"green_score": 96.5})
    assert out["hooks_invoked"] == 1
    assert received == ["audit.completed"]
    assert out["webhook_deliveries_prepared"] == 1
    delivery = out["webhook_deliveries"][0]
    assert delivery["headers"]["X-GreenCode-Event"] == "audit.completed"
    assert delivery["headers"]["X-GreenCode-Signature-256"].startswith("sha256=")


def test_plugin_http_endpoints():
    r_cat = client.get("/api/audit/plugins")
    assert r_cat.status_code == 200
    assert r_cat.json()["total_plugins"] >= 4

    r_wh = client.post(
        "/api/audit/plugins/webhooks",
        json={
            "sink_id": "slack-carbon-alerts",
            "target_url": "https://hooks.slack.com/services/T00/B00/X00",
            "events": ["audit.completed", "budget.breached"],
            "secret": "signing-secret-123",
        },
    )
    assert r_wh.status_code == 200
    assert r_wh.json()["id"] == "slack-carbon-alerts"

    r_disp = client.post(
        "/api/audit/plugins/dispatch-test",
        json={"event_type": "audit.completed", "data": {"green_score": 100.0}},
    )
    assert r_disp.status_code == 200
    assert r_disp.json()["webhook_deliveries_prepared"] >= 1


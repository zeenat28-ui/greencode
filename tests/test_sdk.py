"""Tests for the public Python SDK (app.sdk and app.__init__) and @track_energy."""

from app import GreenCodeSDK, __version__, track_energy


def test_track_energy_context_manager_and_decorator():
    assert __version__ == "2.0.0"

    with track_energy("batch_sum", zone="IE", functional_unit=50.0) as meter:
        total = sum(range(10000))
    assert total > 0
    assert meter.result is not None
    assert meter.result["label"] == "batch_sum"
    assert meter.result["zone"] == "IE"
    assert meter.result["energy_joules"] > 0
    assert meter.result["sci_gco2_per_functional_unit"] > 0

    @track_energy("decorated_work", zone="SE", functional_unit=10.0)
    def compute_squares(n: int) -> int:
        return sum(i * i for i in range(n))

    val = compute_squares(2000)
    assert val > 0
    tracker = getattr(compute_squares, "energy_tracker")
    assert tracker.result is not None
    assert tracker.result["zone"] == "SE"


def test_greencode_sdk_facade():
    sdk = GreenCodeSDK(default_zone="US-CAL-CISO")
    code_res = sdk.audit_code("def f(xs):\n    return [x for x in xs]\n", language="python")
    assert code_res["green_score"] == 100.0

    iac_res = sdk.audit_iac('resource "aws_instance" "x" {\n  instance_type = "m5.xlarge"\n}\n')
    assert iac_res["total_findings"] == 1

    focus_res = sdk.reconcile_focus()
    assert focus_res["line_items_evaluated"] == 3

    if_res = sdk.export_if_manifest(component_name="sdk-service", energy_joules=25.0)
    assert "sdk-service" in if_res["tree"]["children"]


def test_otlp_carbon_exporter_and_endpoint():
    from pathlib import Path
    from fastapi.testclient import TestClient
    from app.main import app

    sdk = GreenCodeSDK(default_zone="EU-SE")
    res = sdk.export_otlp(
        service_name="billing-engine",
        green_score=94.5,
        energy_joules=420.0,
        zone="EU-SE",
    )
    assert res["mode"] == "dry_run_serialized"
    payload = res["payload"]
    assert "resourceMetrics" in payload
    rm = payload["resourceMetrics"][0]
    metrics = rm["scopeMetrics"][0]["metrics"]
    metric_names = {m["name"] for m in metrics}
    assert "greencode.sci.gco2e_per_unit" in metric_names
    assert "greencode.energy.joules" in metric_names
    assert "greencode.audit.green_score" in metric_names

    client = TestClient(app)
    resp = client.post(
        "/api/audit/telemetry/otlp",
        json={"service_name": "api-gw", "green_score": 98.0, "energy_joules": 110.0},
    )
    assert resp.status_code == 200
    assert "resourceMetrics" in resp.json()["payload"]

    otel_src = Path("app/otel_exporter.py").read_text(encoding="utf-8")
    self_audit = sdk.audit_code(otel_src, language="python")
    assert self_audit["green_score"] == 100.0


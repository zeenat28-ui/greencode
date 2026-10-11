"""Tests for Green Software Foundation Impact Framework (.imp.yaml) Manifest Exporter."""

from fastapi.testclient import TestClient

from app.main import app
from app.sci import export_impact_framework_manifest

client = TestClient(app)


def test_export_impact_framework_manifest_structure():
    manifest = export_impact_framework_manifest(
        component_name="checkout-service",
        energy_joules=120.0,
        duration_seconds=30.0,
        carbon_intensity_gco2_per_kwh=250.0,
        functional_unit=500.0,
        vcpu_count=8,
        cloud_instance="c7g.2xlarge",
    )
    assert manifest["name"] == "checkout-service-sci-audit"
    assert "sci" in manifest["initialize"]["plugins"]
    node = manifest["tree"]["children"]["checkout-service"]
    assert node["pipeline"] == ["sci-e", "sci-o", "sci-m", "sci"]
    assert len(node["inputs"]) == 1
    assert len(node["outputs"]) == 1
    out = node["outputs"][0]
    assert out["sci"] > 0
    assert "carbon-operational" in out
    assert "carbon-embodied" in out
    assert "@grnsft/if-plugins" in manifest["yaml_manifest"]


def test_impact_framework_manifest_http_endpoints():
    r_get = client.get("/api/reports/impact-framework-manifest?component_name=api-gateway&energy_joules=80")
    assert r_get.status_code == 200
    body = r_get.json()
    assert "api-gateway" in body["tree"]["children"]

    r_post = client.post(
        "/api/reports/impact-framework-manifest",
        json={
            "component_name": "ml-inference-worker",
            "energy_joules": 450.0,
            "duration_seconds": 60.0,
            "grid_intensity": 95.0,
            "functional_unit": 1000.0,
            "vcpu_count": 16,
            "cloud_instance": "inf2.xlarge",
        },
    )
    assert r_post.status_code == 200
    post_body = r_post.json()
    assert "ml-inference-worker" in post_body["tree"]["children"]
    assert "inf2.xlarge" in post_body["yaml_manifest"]

"""Regression test suite for v2.0.0 Control Plane, AST Loop Rules, Unified Diffs,
Cryptographic License Keys (GC-LIC), and Signed CSRD Evidence Bundles.
"""

import io
import zipfile
from fastapi.testclient import TestClient

from app.main import app
from app.parser import audit_source_code, ViolationType
from app.optimizer import generate_unified_diff, generate_github_suggestion_block
from app.pricing import LicenseKeyManager
from app.auth.jwt import create_tokens
from app.auth.roles import Role


client = TestClient(app)


def _admin_headers():
    """Superadmin token (org 1): exercises secured energy endpoints."""
    tokens = create_tokens(user_id=1, org_id=1, role=Role.SUPERADMIN.value)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_license_key_issuance_and_tamper_rejection():
    """Verify HMAC-SHA256 signed GC-LIC keys validate cleanly and reject tampered payloads."""
    key = LicenseKeyManager.generate_license_key(
        org_id=1,
        tier="pro",
        seats=25,
        expires_days=365,
    )
    assert key.startswith("GC-LIC-")
    verified = LicenseKeyManager.verify_license_key(key)
    assert verified["valid"] is True
    assert verified["tier"] == "pro"
    assert verified["org_id"] == 1
    assert verified["seats"] == 25

    # Tamper with the signature
    tampered = key[:-4] + "0000"
    rejected = LicenseKeyManager.verify_license_key(tampered)
    assert rejected["valid"] is False


def test_heavy_client_instantiation_and_js_loop_hazards():
    """Verify Python SDK client in loop and JS/TS loop hazards are flagged by AST/lexical parser."""
    py_code = (
        "import boto3\n"
        "def upload_batch(items):\n"
        "    for item in items:\n"
        "        s3 = boto3.client('s3')\n"
        "        s3.put_object(Bucket='b', Key=item, Body=b'x')\n"
    )
    py_report = audit_source_code(py_code, file_path="batch.py")
    v_types = [v["violation_type"] for v in py_report["violations"]]
    assert ViolationType.HEAVY_CLIENT_INSTANTIATION_IN_LOOP in v_types

    js_code = (
        "function parsePayloads(rawItems) {\n"
        "  for (let i = 0; i < rawItems.length; i++) {\n"
        "    const obj = JSON.parse(rawItems[i]);\n"
        "    const re = new RegExp('^id-[0-9]+$');\n"
        "  }\n"
        "}\n"
    )
    js_report = audit_source_code(js_code, language="javascript", file_path="worker.js")
    js_types = [v["violation_type"] for v in js_report["violations"]]
    assert ViolationType.JSON_SERIALIZE_IN_LOOP in js_types
    assert ViolationType.INEFFICIENT_REGEX_IN_LOOP in js_types


def test_unified_diff_and_github_suggestion_generation():
    """Verify unified .diff and GitHub PR suggestion markdown blocks are synthesized."""
    orig = "res = []\nfor x in data:\n    res.append(x * 2)\n"
    ref = "res = [x * 2 for x in data]\n"
    diff_text = generate_unified_diff(orig, ref, file_path="app/sample.py")
    assert "--- a/app/sample.py" in diff_text
    assert "+++ b/app/sample.py" in diff_text
    assert "+res = [x * 2 for x in data]" in diff_text

    suggestion = generate_github_suggestion_block(ref)
    assert "```suggestion" in suggestion
    assert "res = [x * 2 for x in data]" in suggestion


def test_energy_control_plane_workloads_and_pr_budget_gate():
    """Verify live 3-tier energy workloads endpoint and PR carbon budget evaluation."""
    res = client.get("/api/energy/workloads", headers=_admin_headers())
    assert res.status_code == 200
    body = res.json()
    assert "telemetry_source" in body
    assert body["telemetry_source"] in (
        "cncf_kepler_prometheus",
        "docker_engine",
        "host_psutil",
    )
    assert isinstance(body["workloads"], list)

    alloc = client.post(
        "/api/energy/budgets/allocate",
        json={"org_id": 1, "team_id": "ci-regression-team", "monthly_budget_kg": 50.0},
        headers=_admin_headers(),
    )
    assert alloc.status_code == 200

    eval_res = client.post(
        "/api/energy/budgets/evaluate-pr",
        json={"org_id": 1, "team_id": "ci-regression-team", "additional_projected_kg_co2e": 0.25},
        headers=_admin_headers(),
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data.get("verdict") in ("PASSED", "WARNING", "BLOCKED")


def test_local_workspace_scanner_and_path_traversal_guard():
    """Verify /api/scan/local-workspace audits valid subdirectories and rejects path traversal."""
    unauthenticated_repositories = client.get("/api/repositories")
    assert unauthenticated_repositories.status_code == 401

    unauthenticated = client.post(
        "/api/scan/local-workspace",
        json={"subpath": "samples"},
    )
    assert unauthenticated.status_code == 401

    registration = client.post(
        "/api/auth/register",
        json={
            "email": "local-scan-test@example.test",
            "username": "local-scan-test",
            "password": "TestPassword123!A",
        },
    )
    assert registration.status_code == 201
    headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}

    repositories = client.get("/api/repositories", headers=headers)
    assert repositories.status_code == 200
    assert isinstance(repositories.json()["repositories"], list)

    valid_res = client.post(
        "/api/scan/local-workspace",
        json={"subpath": "app"},
        headers=headers,
    )
    assert valid_res.status_code == 200
    data = valid_res.json()
    assert data["success"] is True
    assert data["total_files"] >= 1
    assert "recorded_emission_kg" not in data

    history = client.get("/api/history", headers=headers)
    assert history.status_code == 200
    saved_scan = next(
        repo for repo in history.json()["repositories"]
        if repo["id"] == data["repo_id"]
    )
    assert saved_scan["source"] == "local_workspace"
    assert saved_scan["path_or_url"] == "local-workspace/app"

    traversal_res = client.post(
        "/api/scan/local-workspace",
        json={"subpath": "../../Windows"},
        headers=headers,
    )
    assert traversal_res.status_code in (400, 403, 404)


def test_csrd_signed_evidence_bundle_zip():
    """Verify /api/reports/esg/1/evidence-bundle returns a valid signed ZIP with manifest."""
    res = client.get("/api/reports/esg/1/evidence-bundle", headers=_admin_headers())
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/zip"
    assert res.headers.get("X-Bundle-Root-SHA256")

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = zf.namelist()
    assert len(names) >= 2

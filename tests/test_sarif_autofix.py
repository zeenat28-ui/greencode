"""Tests for OASIS SARIF v2.1.0 autofix replacements and SonarQube export endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.parser import audit_source_code
from app.sarif import generate_sarif_report, generate_sonarqube_report

client = TestClient(app)


def test_sarif_report_includes_oasis_compliant_artifact_changes():
    bad_code = (
        "import requests\n"
        "def fetch_all(urls):\n"
        "    out = ''\n"
        "    for u in urls:\n"
        "        r = requests.get(u)\n"
        "        out = out + r.text\n"
        "    return out\n"
    )
    scan = audit_source_code(bad_code, language="python", file_path="worker.py")
    assert len(scan["violations"]) >= 1

    sarif = generate_sarif_report(scan)
    assert sarif["version"] == "2.1.0"
    runs = sarif["runs"]
    assert len(runs) == 1
    assert runs[0]["tool"]["driver"]["version"] == "2.0.0"

    results = runs[0]["results"]
    assert len(results) >= 1
    first = results[0]
    assert "fixes" in first
    fix = first["fixes"][0]
    assert "description" in fix
    assert "artifactChanges" in fix
    assert len(fix["artifactChanges"]) == 1
    change = fix["artifactChanges"][0]
    assert change["artifactLocation"]["uri"] == "worker.py"
    replacement = change["replacements"][0]
    assert replacement["deletedRegion"]["startLine"] >= 1
    assert len(replacement["insertedContent"]["text"].strip()) > 0
    assert first["properties"]["estimated_energy_reduction_pct"] > 0


def test_sarif_and_sonarqube_http_endpoints():
    snippet = (
        "def cube(items):\n"
        "    total = 0\n"
        "    for a in items:\n"
        "        for b in items:\n"
        "            for c in items:\n"
        "                total += a + b + c\n"
        "    return total\n"
    )
    r_sarif = client.post(
        "/api/audit/sarif",
        json={"source_code": snippet, "language": "python", "filename": "calc.py"},
    )
    assert r_sarif.status_code == 200
    body = r_sarif.json()
    assert body["version"] == "2.1.0"
    assert len(body["runs"][0]["results"]) >= 1
    assert "artifactChanges" in body["runs"][0]["results"][0]["fixes"][0]

    r_sonar = client.post(
        "/api/audit/sonarqube",
        json={"source_code": snippet, "language": "python", "filename": "calc.py"},
    )
    assert r_sonar.status_code == 200
    sonar_body = r_sonar.json()
    assert "issues" in sonar_body
    assert len(sonar_body["issues"]) >= 1
    assert sonar_body["issues"][0]["engineId"] == "greencode-auditor"


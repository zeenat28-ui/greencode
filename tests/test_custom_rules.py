"""Tests for the declarative YAML/JSON Custom Energy Rule Engine (.greencode-rules.yaml)."""

from fastapi.testclient import TestClient

from app.custom_rules import evaluate_custom_rules, load_repo_custom_rules, parse_custom_rules_yaml
from app.main import app
from app.parser import audit_source_code

client = TestClient(app)


def test_load_default_custom_rules_and_audit_integration():
    rules = load_repo_custom_rules()
    assert len(rules) >= 4
    rule_ids = {r["id"] for r in rules}
    assert "CUSTOM_SLEEP_POLLING_IN_LOOP" in rule_ids

    snippet = (
        "import time\n"
        "def poll_status(jobs):\n"
        "    for job in jobs:\n"
        "        time.sleep(0.5)\n"
    )
    res = audit_source_code(snippet, language="python", file_path="poller.py")
    vtypes = [v["violation_type"] for v in res["violations"]]
    assert "CUSTOM_SLEEP_POLLING_IN_LOOP" in vtypes


def test_custom_rules_http_endpoints():
    r_list = client.get("/api/policies/custom-rules")
    assert r_list.status_code == 200
    data = r_list.json()
    assert data["count"] >= 4

    custom_yaml = (
        "rules:\n"
        "  - id: ORG_NO_BOTO3_SCAN\n"
        "    title: DynamoDB Full Table Scan Prohibited\n"
        "    description: Full table scans consume excessive RCUs and storage I/O energy.\n"
        "    pattern_regex: '\\.scan\\s*\\('\n"
        "    languages: ['python']\n"
        "    severity: HIGH\n"
        "    deduction: 12.0\n"
        "    gsf_pattern: GSF-DB-INDEXED-QUERY\n"
        "    fix_guidance: Use table.query() with a KeyConditionExpression instead of table.scan().\n"
    )
    r_eval = client.post(
        "/api/policies/custom-rules/evaluate",
        json={
            "source_code": "items = dynamo_table.scan(FilterExpression='active=1')\n",
            "language": "python",
            "file_path": "repo_dao.py",
            "rules_yaml": custom_yaml,
        },
    )
    assert r_eval.status_code == 200
    body = r_eval.json()
    assert body["violations_count"] == 1
    assert body["violations"][0]["violation_type"] == "ORG_NO_BOTO3_SCAN"
    assert body["green_score"] == 88.0

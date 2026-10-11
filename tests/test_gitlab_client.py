"""Tests for GitLab Merge Request Carbon Gate & Comment Bot."""

from fastapi.testclient import TestClient

from app.gitlab_client import build_gitlab_mr_carbon_comment, generate_gitlab_suggestion_block
from app.main import app
from app.parser import audit_source_code

client = TestClient(app)


def test_gitlab_suggestion_and_mr_comment_generation():
    block = generate_gitlab_suggestion_block("x = ''.join(items)", lines_above=0, lines_below=2)
    assert "```suggestion:-0+2" in block
    assert "x = ''.join(items)" in block

    bad_code = (
        "def concat_all(words):\n"
        "    out = ''\n"
        "    for w in words:\n"
        "        out = out + w\n"
        "    return out\n"
    )
    scan = audit_source_code(bad_code, language="python", file_path="src/strings.py")
    comment = build_gitlab_mr_carbon_comment(scan, threshold=75.0, zone="DE")
    assert "<!-- greencode-gitlab-mr-comment -->" in comment
    assert "```suggestion:-0+" in comment
    assert "```diff" in comment


def test_gitlab_preview_and_webhook_endpoints():
    snippet = (
        "def nested_sum(items):\n"
        "    s = 0\n"
        "    for a in items:\n"
        "        for b in items:\n"
        "            for c in items:\n"
        "                s += a + b + c\n"
        "    return s\n"
    )
    r_prev = client.post(
        "/api/pr-gate/gitlab-preview",
        json={
            "project_id": "acme/payments",
            "mr_iid": 42,
            "source_code": snippet,
            "language": "python",
            "file_path": "payments/calc.py",
        },
    )
    assert r_prev.status_code == 200
    body = r_prev.json()
    assert body["project_id"] == "acme/payments"
    assert body["mr_iid"] == 42
    assert "```suggestion:-0+" in body["markdown"]

    r_hook = client.post(
        "/api/pr-gate/gitlab-webhook",
        json={
            "object_kind": "merge_request",
            "project": {"path_with_namespace": "acme/payments"},
            "object_attributes": {"iid": 42},
            "source_code": snippet,
        },
    )
    assert r_hook.status_code == 200
    hook_body = r_hook.json()
    assert hook_body["violations_count"] >= 1
    assert "<!-- greencode-gitlab-mr-comment -->" in hook_body["comment_markdown"]

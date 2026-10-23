from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.main import app


def test_github_authorize_requires_state():
    response = TestClient(app).get("/api/auth/github/authorize")

    assert response.status_code == 422


def test_github_authorize_preserves_state_redirect_and_repo_scope(monkeypatch):
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test-client-secret")
    state = "unguessable-state-value-for-oauth-test"
    redirect_uri = "http://localhost:5173/login"

    response = TestClient(app).get(
        "/api/auth/github/authorize",
        params={"redirect_uri": redirect_uri, "state": state},
    )

    assert response.status_code == 200
    payload = response.json()
    auth_query = parse_qs(urlparse(payload["auth_url"]).query)
    assert auth_query["state"] == [state]
    assert auth_query["redirect_uri"] == [redirect_uri]
    assert "repo" in auth_query["scope"][0].split(",")

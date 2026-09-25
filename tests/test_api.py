"""API Integration Test Suite for GreenCode Auditor.

Covers the GitHub-only pipeline end to end:
- POST /api/auth/github  (GitHub token sign-in)
- GET  /github/repos     (repository listing)
- POST /api/scan/github  (synchronous audit)
- POST /api/scan/github/async + GET /api/task/{id} (background audit)
- GET  /api/history      (user-scoped, paginated)
- GET  /api/profile/benchmarks + POST /api/profile (whitelisted profiler)
- GET  /api/auth/me, /api/auth/refresh, /api/auth/logout

Network calls to GitHub are mocked; the audit engine, database layer, auth and
ownership checks all run for real.
"""

import os
import sys
import tempfile
import time
import unittest
import uuid
import zipfile
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import init_db
from app.main import app


SAMPLES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))

PREFLIGHT_OK = {
    "can_audit": True,
    "language": "Python",
    "size_kb": 900,
    "default_branch": "main",
    "archived": False,
    "full_name": "zeenat28-ui/greencode",
    "html_url": "https://github.com/zeenat28-ui/greencode",
}


def make_zipball(root: str = "zeenat28-ui-greencode-a1b2c3d4") -> str:
    """Build a GitHub-style zipball (single synthetic top-level directory)."""
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{root}/README.md", "# demo\n")
        z.writestr(
            f"{root}/heavy_pipeline.py",
            "import requests\n"
            "for a in items:\n"
            "    for b in items:\n"
            "        for c in items:\n"
            "            requests.get('https://x/')\n",
        )
        z.writestr(f"{root}/src/app.py", "x = 1\n")
    return path


def mock_response(status_code=200, payload=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload if payload is not None else {}
    resp.text = text
    resp.content = text.encode()
    resp.close = MagicMock()
    resp.iter_content = MagicMock(return_value=iter([]))
    return resp


class TestPublicEndpoints(unittest.TestCase):
    """Endpoints that must work without authentication."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "GreenCode Auditor API")
        self.assertEqual(data["status"], "online")

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "GreenCode Auditor")
        self.assertIn(data["status"], ("healthy", "degraded"))
        self.assertIn("database", data["deps"])

    def test_grid_zones_endpoint(self):
        resp = self.client.get("/api/grid/zones")
        self.assertEqual(resp.status_code, 200)
        zones = resp.json()
        self.assertGreater(len(zones), 0)
        self.assertIn("US-CAL-CISO", [z["zone"] for z in zones])

    def test_grid_zone_intensity_endpoint(self):
        resp = self.client.get("/api/grid/zone/US-CAL-CISO")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("carbon_intensity", data)
        self.assertGreater(data["carbon_intensity"], 0)

    def test_badge_score_endpoint(self):
        resp = self.client.get("/api/badge/score/88.5")
        self.assertEqual(resp.status_code, 200)


class TestAuthRequired(unittest.TestCase):
    """Every data endpoint must reject anonymous callers."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_protected_endpoints_require_auth(self):
        protected = [
            ("get", "/api/task/anything", None),
            ("get", "/api/history", None),
            ("get", "/github/user", None),
            ("get", "/github/repos", None),
            ("get", "/api/profile/benchmarks", None),
            ("get", "/api/auth/me", None),
            ("post", "/api/scan/github", {"repo": "a/b"}),
            ("post", "/api/scan/github/async", {"repo": "a/b"}),
            ("post", "/api/profile", {"benchmark": "heavy_pipeline"}),
            ("post", "/api/refactor", {"snippet": "x=1", "violation_type": "NESTED_LOOPS_DEPTH_3+"}),
        ]
        for method, path, body in protected:
            with self.subTest(path=path):
                resp = self.client.get(path) if method == "get" else self.client.post(path, json=body)
                self.assertEqual(resp.status_code, 401, f"{path} should require auth")


class TestRemovedEndpoints(unittest.TestCase):
    """Local-folder and ZIP-upload flows must be gone in GitHub-only mode."""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_local_scan_routes_removed(self):
        paths = {r.path for r in app.routes if hasattr(r, "path")}
        for gone in (
            "/api/scan",
            "/api/scan/upload",
            "/api/scan/async",
            "/api/scan/sarif",
            "/api/ci/evaluate",
            "/api/auth/signup",
            "/api/auth/signin",
            "/api/auth/forgot-password",
            "/api/auth/reset-password",
        ):
            self.assertNotIn(gone, paths, f"{gone} should have been removed")

    def test_removed_endpoints_return_404(self):
        self.assertEqual(self.client.post("/api/scan", json={"repo_path": "."}).status_code, 404)
        self.assertEqual(self.client.post("/api/scan/upload").status_code, 404)


class TestAuthenticatedPipeline(unittest.TestCase):
    """Full GitHub sign-in -> scan -> history flow with mocked GitHub HTTP."""

    token = None
    user_id = None

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def _01_github_signin(self):
        with patch("app.github_client._request") as mock_req:
            mock_req.return_value = mock_response(200, {
                "login": f"tester_{uuid.uuid4().hex[:6]}",
                "id": 12345,
                "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                "name": "Test User",
            })
            resp = self.client.post("/api/auth/github", json={"github_token": "ghp_" + "a" * 36})
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        # The raw token must never be echoed back to the client.
        self.assertNotIn("ghp_" + "a" * 36, resp.text)
        TestAuthenticatedPipeline.token = data["access_token"]
        TestAuthenticatedPipeline.user_id = data["user"]["id"]

    def _02_auth_me(self):
        resp = self.client.get("/api/auth/me", headers=self._h())
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["authenticated"])

    def _03_list_repos(self):
        repo_payload = [{
            "full_name": "zeenat28-ui/greencode", "name": "greencode",
            "owner": {"login": "zeenat28-ui"}, "default_branch": "main",
            "language": "Python", "description": "Carbon auditor", "size": 900,
            "private": False, "fork": False, "archived": False,
            "stargazers_count": 3, "forks_count": 1, "open_issues_count": 0,
            "updated_at": "2026-01-01T00:00:00Z",
            "html_url": "https://github.com/zeenat28-ui/greencode",
        }]
        with patch("app.github_client._request", return_value=mock_response(200, repo_payload)):
            resp = self.client.get("/github/repos", headers=self._h())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["repositories"][0]["full_name"], "zeenat28-ui/greencode")

    def _04_sync_github_scan(self):
        tmp_zip = make_zipball()
        # Patch where the names are bound - app.scanner imports them directly.
        with patch("app.scanner.inspect_repository_before_audit", return_value=PREFLIGHT_OK), \
             patch("app.scanner.download_repository_archive", return_value=tmp_zip), \
             patch("app.github_client.inspect_repository_before_audit", return_value=PREFLIGHT_OK):
            resp = self.client.post(
                "/api/scan/github",
                json={"repo": "https://github.com/zeenat28-ui/greencode"},
                headers=self._h(),
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()

        self.assertEqual(data["full_name"], "zeenat28-ui/greencode")
        self.assertTrue(data["is_github"])
        self.assertEqual(data["source"], "github")
        self.assertEqual(data["ref"], "main")
        self.assertIn("repo_id", data)
        self.assertGreater(data["total_files"], 0)
        self.assertEqual(data["repo_path"], "zeenat28-ui/greencode")

        # Paths must be repository-relative, not absolute temp workspace paths.
        for v in data["violations"]:
            self.assertFalse(os.path.isabs(v["file_path"]), v["file_path"])
            self.assertNotIn("greencode-a1b2c3d4", v["file_path"])

    def _05_history_is_user_scoped(self):
        resp = self.client.get("/api/history", headers=self._h())
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("cumulative_savings", data)
        self.assertIn("has_more", data)
        for repo in data["repositories"]:
            self.assertEqual(repo["user_id"], self.user_id)
            self.assertEqual(repo["source"], "github")
        self.assertTrue(any(r["full_name"] == "zeenat28-ui/greencode" for r in data["repositories"]))

    def _06_async_scan_and_polling(self):
        tmp_zip = make_zipball()
        with patch("app.scanner.inspect_repository_before_audit", return_value=PREFLIGHT_OK), \
             patch("app.scanner.download_repository_archive", return_value=tmp_zip), \
             patch("app.github_client.inspect_repository_before_audit", return_value=PREFLIGHT_OK):
            resp = self.client.post(
                "/api/scan/github/async",
                json={"repo": "zeenat28-ui/greencode"},
                headers=self._h(),
            )
        self.assertEqual(resp.status_code, 200, resp.text)
        task_id = resp.json()["task_id"]
        self.assertTrue(task_id)

        final = None
        for _ in range(80):
            poll = self.client.get(f"/api/task/{task_id}", headers=self._h())
            self.assertEqual(poll.status_code, 200)
            final = poll.json()
            if final.get("is_done"):
                break
            time.sleep(0.25)

        self.assertTrue(final.get("is_done"), "async task did not complete in time")
        self.assertEqual(final["status"], "Completed")
        self.assertEqual(final["result"]["full_name"], "zeenat28-ui/greencode")

    def _07_unknown_task_is_404(self):
        self.assertEqual(
            self.client.get("/api/task/does-not-exist", headers=self._h()).status_code, 404
        )

    def _08_profiler_whitelist(self):
        resp = self.client.get("/api/profile/benchmarks", headers=self._h())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("heavy_pipeline", [b["id"] for b in resp.json()["benchmarks"]])

        # Arbitrary paths must be rejected - this is the RCE guard.
        bad = self.client.post(
            "/api/profile",
            json={"benchmark": "../../../../Windows/System32/drivers/etc/hosts"},
            headers=self._h(),
        )
        self.assertEqual(bad.status_code, 404)

    def _09_profiler_runs_benchmark(self):
        resp = self.client.post(
            "/api/profile",
            json={"benchmark": "eco_pipeline", "timeout_sec": 10.0, "zone": "US-CAL-CISO"},
            headers=self._h(),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertEqual(data["benchmark"], "eco_pipeline")
        self.assertIn("energy_wh", data)
        self.assertIn("sci_score_gco2", data)

    def _10_refactor_endpoint(self):
        resp = self.client.post(
            "/api/refactor",
            json={
                "snippet": "for i in a:\n    for j in b:\n        for k in c:\n            v = i*j*k",
                "violation_type": "NESTED_LOOPS_DEPTH_3+",
            },
            headers=self._h(),
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertGreater(resp.json()["energy_reduction_pct"], 0)

    def _11_github_url_validation(self):
        resp = self.client.post("/api/scan/github", json={"repo": "not a repo"}, headers=self._h())
        self.assertEqual(resp.status_code, 400)
        self.assertIn("owner/repo", resp.json()["detail"])

    def _12_refresh_rotation_and_logout(self):
        gh_user = {"login": "refresh_user", "id": 999, "avatar_url": "", "name": "R"}
        with patch("app.github_client._request", return_value=mock_response(200, gh_user)):
            login = self.client.post("/api/auth/github", json={"github_token": "ghp_" + "b" * 36})
        self.assertEqual(login.status_code, 200)
        old_refresh = login.json()["refresh_token"]

        rotated = self.client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        self.assertEqual(rotated.status_code, 200)
        new_access = rotated.json()["access_token"]
        new_refresh = rotated.json()["refresh_token"]
        self.assertNotEqual(old_refresh, new_refresh)

        # The rotated-away refresh token must no longer be usable.
        replay = self.client.post("/api/auth/refresh", json={"refresh_token": old_refresh})
        self.assertEqual(replay.status_code, 401)

        out = self.client.post("/api/auth/logout", headers={"Authorization": f"Bearer {new_access}"})
        self.assertEqual(out.status_code, 200)
        after = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access}"})
        self.assertEqual(after.status_code, 401)

    def _13_idor_protection(self):
        resp = self.client.get("/api/auth/user/999999", headers=self._h())
        self.assertEqual(resp.status_code, 403)

    def test_full_pipeline(self):
        for step in (
            self._01_github_signin,
            self._02_auth_me,
            self._03_list_repos,
            self._04_sync_github_scan,
            self._05_history_is_user_scoped,
            self._06_async_scan_and_polling,
            self._07_unknown_task_is_404,
            self._08_profiler_whitelist,
            self._09_profiler_runs_benchmark,
            self._10_refactor_endpoint,
            self._11_github_url_validation,
            self._12_refresh_rotation_and_logout,
            self._13_idor_protection,
        ):
            with self.subTest(step=step.__name__):
                step()


if __name__ == "__main__":
    unittest.main()

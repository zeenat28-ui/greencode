"""Unit Tests for the GitHub Client in GreenCode Auditor.

The client issues every call through a pooled `requests.Session`, so these
tests patch the session's `request` method rather than the module-level
`requests.get/post/put` helpers.
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.github_client import (
    GitHubAPIError,
    create_refactoring_pull_request,
    download_repository_archive,
    get_authenticated_user,
    inspect_repository_before_audit,
    list_repository_branches,
    list_user_repositories,
    normalize_repo_slug,
)


def _resp(status_code=200, payload=None, content=b""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload if payload is not None else {}
    resp.text = "mock"
    resp.content = content
    resp.close = MagicMock()
    resp.iter_content = MagicMock(return_value=iter([content] if content else []))
    return resp


class TestRepoSlugNormalisation(unittest.TestCase):
    def test_accepts_common_formats(self):
        for raw in (
            "owner/repo",
            "https://github.com/owner/repo",
            "http://github.com/owner/repo/",
            "https://github.com/owner/repo.git",
            "  owner/repo  ",
        ):
            self.assertEqual(normalize_repo_slug(raw), "owner/repo", raw)

    def test_rejects_invalid(self):
        for bad in ("", "not a repo", "owner", "owner/repo/extra", "../../etc"):
            with self.assertRaises(ValueError, msg=bad):
                normalize_repo_slug(bad)


class TestGitHubClient(unittest.TestCase):
    @patch("app.github_client._get_session")
    def test_get_authenticated_user(self, mock_session):
        mock_session.return_value.request.return_value = _resp(200, {"login": "testuser", "id": 12345})
        user = get_authenticated_user(token="fake_token")
        self.assertIsNotNone(user)
        self.assertEqual(user["login"], "testuser")

    @patch("app.github_client._get_session")
    def test_list_user_repositories(self, mock_session):
        payload = [{
            "full_name": "testuser/repo1", "name": "repo1", "default_branch": "main",
            "language": "Python", "size": 10, "private": False, "fork": False,
            "archived": False, "stargazers_count": 0, "forks_count": 0,
            "open_issues_count": 0, "updated_at": "", "html_url": "u", "owner": {"login": "testuser"},
        }]
        mock_session.return_value.request.return_value = _resp(200, payload)
        repos = list_user_repositories(token="fake_token")
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["full_name"], "testuser/repo1")
        self.assertIn("stars", repos[0])

    @patch("app.github_client._get_session")
    def test_list_repository_branches(self, mock_session):
        mock_session.return_value.request.return_value = _resp(
            200, [{"name": "main", "commit": {"sha": "abc"}}, {"name": "dev", "commit": {"sha": "def"}}]
        )
        branches = list_repository_branches("testuser/repo1", token="fake_token")
        self.assertEqual([b["name"] for b in branches], ["main", "dev"])

    @patch("app.github_client._get_session")
    def test_download_repository_archive(self, mock_session):
        mock_session.return_value.request.return_value = _resp(200, content=b"PK\x03\x04fake")
        zip_path = download_repository_archive("testuser/repo1", token="fake_token")
        self.assertTrue(os.path.exists(zip_path))
        os.remove(zip_path)

    @patch("app.github_client._get_session")
    def test_download_repository_archive_raises_on_404(self, mock_session):
        mock_session.return_value.request.return_value = _resp(404, {"message": "Not Found"})
        with self.assertRaises(GitHubAPIError) as ctx:
            download_repository_archive("testuser/missing", token="fake_token")
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.github_client._get_session")
    def test_inspect_raises_on_404(self, mock_session):
        mock_session.return_value.request.return_value = _resp(404, {"message": "Not Found"})
        with self.assertRaises(GitHubAPIError) as ctx:
            inspect_repository_before_audit("testuser/missing", token="fake_token")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_inspect_cache_is_credential_scoped(self):
        """Cache keys must not let one user's token serve another user's metadata."""
        from app.github_client import _cache_fingerprint

        a = _cache_fingerprint("token_aaa")
        b = _cache_fingerprint("token_bbb")
        self.assertNotEqual(a, b)
        self.assertEqual(a, _cache_fingerprint("token_aaa"))
        # The raw token must never be embedded in the key.
        self.assertNotIn("token_aaa", a)


    @patch("app.github_client._get_session")
    def test_create_refactoring_pull_request(self, mock_session):
        mock_request = mock_session.return_value.request
        # Single call order: repo -> ref -> create branch -> contents -> PUT file -> open PR
        mock_request.side_effect = [
            _resp(200, {"default_branch": "main"}),
            _resp(200, {"object": {"sha": "abc123sha"}}),
            _resp(201, {"ref": "refs/heads/greencode/eco-refactor-1"}),
            _resp(404, {"message": "Not Found"}),
            _resp(201, {"content": {"sha": "x"}}),
            _resp(201, {"html_url": "https://github.com/testuser/repo1/pull/1", "number": 1}),
        ]

        result = create_refactoring_pull_request(
            repo_full_name="testuser/repo1",
            file_path="samples/test.py",
            refactored_code="print('optimized')",
            violation_title="NESTED_LOOPS",
            energy_reduction_pct=50.0,
            carbon_saved_10k=30.0,
            token="fake_token",
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["pr_number"], 1)
        self.assertIn("https://github.com/testuser/repo1/pull/1", result["pr_url"])

    @patch("app.github_client._get_session")
    def test_create_refactoring_pull_request_with_remote_patching(self, mock_session):
        """Verify GitHub PR fetches remote multi-line file and patches only the target snippet."""
        import base64

        remote_source = (
            "import os\n"
            "\n"
            "def run_pipeline():\n"
            "    data = [1, 2, 3]\n"
            "    for a in data:\n"
            "        for b in data:\n"
            "            for c in data:\n"
            "                print(a, b, c)\n"
            "    return True\n"
        )
        original_snippet = (
            "    for a in data:\n"
            "        for b in data:\n"
            "            for c in data:\n"
            "                print(a, b, c)"
        )
        refactored_snippet = (
            "from itertools import product\n"
            "for a, b, c in product(data, repeat=3):\n"
            "    print(a, b, c)"
        )

        file_payload = {
            "sha": "blobsha456",
            "content": base64.b64encode(remote_source.encode("utf-8")).decode("utf-8"),
        }
        mock_request = mock_session.return_value.request
        mock_request.side_effect = [
            _resp(200, {"default_branch": "main"}),
            _resp(200, {"object": {"sha": "basesha123"}}),
            _resp(201, {"ref": "refs/heads/greencode/eco-refactor-2"}),
            _resp(200, file_payload),
            _resp(201, {"content": {"sha": "x"}}),
            _resp(201, {"html_url": "https://github.com/testuser/repo1/pull/2", "number": 2}),
        ]

        result = create_refactoring_pull_request(
            repo_full_name="testuser/repo1",
            file_path="src/pipeline.py",
            refactored_code=refactored_snippet,
            original_snippet=original_snippet,
            violation_title="NESTED_LOOPS",
            energy_reduction_pct=60.0,
            carbon_saved_10k=45.0,
            token="fake_token",
        )

        self.assertTrue(result["success"], result)
        self.assertEqual(result["pr_number"], 2)

        # Locate the PUT /contents call and decode what was committed.
        put_call = next(
            c for c in mock_request.call_args_list
            if c.args and c.args[0] == "PUT"
        )
        put_payload = put_call.kwargs["json"]
        committed_code = base64.b64decode(put_payload["content"]).decode("utf-8")

        # Must retain overall file structure
        self.assertIn("def run_pipeline():", committed_code)
        self.assertIn("return True", committed_code)
        # Must contain patched code properly indented
        self.assertIn("for a, b, c in product(data, repeat=3):", committed_code)

    @patch("app.github_client._get_session")
    def test_create_refactoring_pull_request_syntax_error_prevention(self, mock_session):
        """Verify that malformed or syntax-error refactored code is blocked before commit."""
        import base64

        remote_source = "def run():\n    x = 10\n    return x\n"
        original_snippet = "    x = 10"
        broken_refactored_code = "    x = (10 +"  # Unclosed parenthesis -> SyntaxError

        file_payload = {
            "sha": "blobsha456",
            "content": base64.b64encode(remote_source.encode("utf-8")).decode("utf-8"),
        }
        mock_request = mock_session.return_value.request
        mock_request.side_effect = [
            _resp(200, {"default_branch": "main"}),
            _resp(200, {"object": {"sha": "basesha123"}}),
            _resp(200, file_payload),
            _resp(201, {"ref": "refs/heads/greencode/eco-refactor-3"}),
        ]

        result = create_refactoring_pull_request(
            repo_full_name="testuser/repo1",
            file_path="src/broken.py",
            refactored_code=broken_refactored_code,
            original_snippet=original_snippet,
            violation_title="ENERGY",
            token="fake_token",
        )

        self.assertFalse(result["success"])
        self.assertIn("syntax", result["error"].lower())
        # A PUT to /contents must never be issued with invalid code.
        put_calls = [c for c in mock_request.call_args_list if c.args and c.args[0] == "PUT"]
        self.assertEqual(put_calls, [])


if __name__ == "__main__":
    unittest.main()


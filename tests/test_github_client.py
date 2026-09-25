"""Unit Tests for GitHub Client in GreenCode Auditor."""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.github_client import (
    create_refactoring_pull_request,
    download_repository_archive,
    get_authenticated_user,
    list_user_repositories,
)


class TestGitHubClient(unittest.TestCase):
    @patch("requests.get")
    def test_get_authenticated_user(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"login": "testuser", "id": 12345}
        mock_get.return_value = mock_resp

        user = get_authenticated_user(token="fake_token")
        self.assertIsNotNone(user)
        self.assertEqual(user["login"], "testuser")

    @patch("requests.get")
    def test_list_user_repositories(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"full_name": "testuser/repo1", "name": "repo1", "default_branch": "main", "private": False, "html_url": "https://github.com/testuser/repo1"}
        ]
        mock_get.return_value = mock_resp

        repos = list_user_repositories(token="fake_token")
        self.assertEqual(len(repos), 1)
        self.assertEqual(repos[0]["full_name"], "testuser/repo1")

    @patch("requests.get")
    def test_download_repository_archive(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"PK\x03\x04fake_zip_content"
        mock_get.return_value = mock_resp

        zip_path = download_repository_archive("testuser/repo1", token="fake_token")
        self.assertIsNotNone(zip_path)
        self.assertTrue(os.path.exists(zip_path))
        os.remove(zip_path)

    @patch("requests.post")
    @patch("requests.put")
    @patch("requests.get")
    def test_create_refactoring_pull_request(self, mock_get, mock_put, mock_post):
        # 1. repo info
        resp_repo = MagicMock(status_code=200)
        resp_repo.json.return_value = {"default_branch": "main"}

        # 2. git ref
        resp_ref = MagicMock(status_code=200)
        resp_ref.json.return_value = {"object": {"sha": "abc123sha"}}

        # 3. file contents
        resp_file = MagicMock(status_code=404)

        mock_get.side_effect = [resp_repo, resp_ref, resp_file]

        # 4. create branch post
        resp_branch = MagicMock(status_code=201)
        resp_branch.json.return_value = {"ref": "refs/heads/greencode/eco-refactor-1"}

        # 5. open pr post
        resp_pr = MagicMock(status_code=201)
        resp_pr.json.return_value = {"html_url": "https://github.com/testuser/repo1/pull/1", "number": 1}

        mock_post.side_effect = [resp_branch, resp_pr]

        # 6. put file content
        resp_put = MagicMock(status_code=201)
        mock_put.return_value = resp_put

        result = create_refactoring_pull_request(
            repo_full_name="testuser/repo1",
            file_path="samples/test.py",
            refactored_code="print('optimized')",
            violation_title="NESTED_LOOPS",
            energy_reduction_pct=50.0,
            carbon_saved_10k=30.0,
            token="fake_token",
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["pr_number"], 1)
        self.assertIn("https://github.com/testuser/repo1/pull/1", result["pr_url"])

    @patch("requests.post")
    @patch("requests.put")
    @patch("requests.get")
    def test_create_refactoring_pull_request_with_remote_patching(self, mock_get, mock_put, mock_post):
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

        resp_repo = MagicMock(status_code=200)
        resp_repo.json.return_value = {"default_branch": "main"}

        resp_ref = MagicMock(status_code=200)
        resp_ref.json.return_value = {"object": {"sha": "basesha123"}}

        # Mock existing remote file on GitHub
        resp_file = MagicMock(status_code=200)
        resp_file.json.return_value = {
            "sha": "blobsha456",
            "content": base64.b64encode(remote_source.encode("utf-8")).decode("utf-8"),
        }

        mock_get.side_effect = [resp_repo, resp_ref, resp_file]

        resp_branch = MagicMock(status_code=201)
        resp_branch.json.return_value = {"ref": "refs/heads/greencode/eco-refactor-2"}

        resp_pr = MagicMock(status_code=201)
        resp_pr.json.return_value = {"html_url": "https://github.com/testuser/repo1/pull/2", "number": 2}

        mock_post.side_effect = [resp_branch, resp_pr]

        resp_put = MagicMock(status_code=201)
        mock_put.return_value = resp_put

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

        self.assertTrue(result["success"])
        self.assertEqual(result["pr_number"], 2)

        # Inspect what was actually committed
        put_call_args = mock_put.call_args
        put_payload = put_call_args[1]["json"]
        committed_code = base64.b64decode(put_payload["content"]).decode("utf-8")

        # Must retain overall file structure
        self.assertIn("def run_pipeline():", committed_code)
        self.assertIn("return True", committed_code)
        # Must contain patched code properly indented
        self.assertIn("for a, b, c in product(data, repeat=3):", committed_code)

    @patch("requests.post")
    @patch("requests.put")
    @patch("requests.get")
    def test_create_refactoring_pull_request_syntax_error_prevention(self, mock_get, mock_put, mock_post):
        """Verify that malformed or syntax-error refactored code is blocked before commit."""
        import base64

        remote_source = "def run():\n    x = 10\n    return x\n"
        original_snippet = "    x = 10"
        broken_refactored_code = "    x = (10 +"  # Unclosed parenthesis -> SyntaxError

        resp_repo = MagicMock(status_code=200)
        resp_repo.json.return_value = {"default_branch": "main"}

        resp_ref = MagicMock(status_code=200)
        resp_ref.json.return_value = {"object": {"sha": "basesha123"}}

        resp_file = MagicMock(status_code=200)
        resp_file.json.return_value = {
            "sha": "blobsha456",
            "content": base64.b64encode(remote_source.encode("utf-8")).decode("utf-8"),
        }

        mock_get.side_effect = [resp_repo, resp_ref, resp_file]

        resp_branch = MagicMock(status_code=201)
        resp_branch.json.return_value = {"ref": "refs/heads/greencode/eco-refactor-3"}
        mock_post.return_value = resp_branch

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
        # Verify that PUT was never called with invalid code
        mock_put.assert_not_called()


if __name__ == "__main__":
    unittest.main()


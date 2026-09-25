"""Automated Test Suite for GreenCode Auditor Authentication & Access Control.

Tests User model, bcrypt hashing, credential verification, GitHub OAuth/PAT integration,
and FastAPI authentication endpoints (/api/auth/*).
"""

import os
import sys
import unittest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import (
    authenticate_user,
    create_password_reset_token,
    create_user,
    get_or_create_github_user,
    get_repository_details,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    hash_password,
    init_db,
    reset_password_with_token,
    save_scan_results,
    update_user_profile,
    verify_password,
    verify_user_email,
)
from app.main import app


class TestAuthDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_password_hashing_and_verification(self):
        """Verify bcrypt produces valid hashes and verifies correctly."""
        raw_pw = "SuperSecurePassword123!"
        hashed = hash_password(raw_pw)

        self.assertNotEqual(raw_pw, hashed)
        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertTrue(verify_password(raw_pw, hashed))
        self.assertFalse(verify_password("WrongPassword999", hashed))

    def test_02_create_user_and_authenticate(self):
        """Verify user creation with email and password, and sign in via email or username."""
        uid = uuid.uuid4().hex[:8]
        email = f"test_{uid}@greencode.io"
        username = f"user_{uid}"
        raw_pw = "P@ssw0rd2026!"

        user = create_user(
            email=email,
            username=username,
            password=raw_pw,
            full_name=f"Test User {uid}",
            role="lead",
        )

        self.assertIsNotNone(user)
        self.assertEqual(user["email"], email)
        self.assertEqual(user["username"], username)
        self.assertEqual(user["role"], "lead")

        # Authenticate by email
        auth_email = authenticate_user(email, raw_pw)
        self.assertIsNotNone(auth_email)
        self.assertEqual(auth_email["id"], user["id"])

        # Authenticate by username
        auth_user = authenticate_user(username, raw_pw)
        self.assertIsNotNone(auth_user)
        self.assertEqual(auth_user["id"], user["id"])

        # Authenticate with wrong password fails
        bad_pw = authenticate_user(email, "WrongPass!")
        self.assertIsNone(bad_pw)

    def test_03_duplicate_prevention(self):
        """Verify unique constraints prevent duplicate email or username registration."""
        uid = uuid.uuid4().hex[:8]
        email = f"dup_{uid}@greencode.io"
        username = f"dup_{uid}"
        raw_pw = "SecretKey123!"

        create_user(email=email, username=username, password=raw_pw)

        # Attempt duplicate email
        with self.assertRaises(ValueError) as ctx:
            create_user(email=email, username=f"other_{uid}", password=raw_pw)
        self.assertIn("already exists", str(ctx.exception))

        # Attempt duplicate username
        with self.assertRaises(ValueError) as ctx:
            create_user(email=f"other_{uid}@greencode.io", username=username, password=raw_pw)
        self.assertIn("already taken", str(ctx.exception))

    def test_04_github_user_provisioning(self):
        """Verify get_or_create_github_user creates new account or links existing account."""
        uid = uuid.uuid4().hex[:8]
        gh_user = f"gh_{uid}"
        gh_email = f"gh_{uid}@github.com"
        avatar = f"https://avatars.githubusercontent.com/u/{uid}"

        user = get_or_create_github_user(
            github_token="ghp_mock_token_for_test",
            gh_user_data={
                "login": gh_user,
                "email": gh_email,
                "avatar_url": avatar,
                "name": f"GitHub User {uid}",
            },
        )

        self.assertIsNotNone(user)
        self.assertEqual(user["github_username"], gh_user)
        self.assertEqual(user["avatar_url"], avatar)

        # Calling again should update / return the same user
        user_repeat = get_or_create_github_user(
            github_token="ghp_updated_token",
            gh_user_data={
                "login": gh_user,
                "email": gh_email,
                "avatar_url": avatar,
                "name": f"GitHub User {uid}",
            },
        )
        self.assertEqual(user["id"], user_repeat["id"])

        # The raw token must NEVER be returned by this function - it feeds
        # directly into the /api/auth/github HTTP response.
        self.assertIsNone(user_repeat["github_token"])
        self.assertTrue(user_repeat["has_github_token"])
        # Only a masked hint is exposed for the UI (e.g. "ghp_****aaaa").
        self.assertIsNotNone(user_repeat["github_token_masked"])
        self.assertIn("****", user_repeat["github_token_masked"])
        self.assertNotIn("ghp_updated_token", str(user_repeat))

    def test_05_repository_scan_linked_to_user(self):
        """Verify audit scan records can be associated with a user_id."""
        uid = uuid.uuid4().hex[:8]
        user = create_user(email=f"scan_{uid}@greencode.io", username=f"scan_{uid}", password="Password123!")

        repo_name = f"user_{uid}/green-repo"
        repo_obj = save_scan_results(
            name=repo_name,
            path_or_url=f"https://github.com/{repo_name}",
            total_files=5,
            total_lines=250,
            green_score=92.5,
            violations_data=[],
            user_id=user["id"],
        )

        details = get_repository_details(repo_obj.id)
        self.assertIsNotNone(details)
        self.assertEqual(details["user_id"], user["id"])

    def test_06_email_verification(self):
        """Verify email verification token generation and activation."""
        uid = uuid.uuid4().hex[:8]
        user = create_user(
            email=f"verify_{uid}@greencode.io",
            username=f"verify_{uid}",
            password="Password123!",
            auto_verify=False,
        )
        self.assertFalse(user["is_verified"])
        self.assertIsNotNone(user["verification_token"])

        # Invalid token returns failure
        invalid_res = verify_user_email("fake_token_12345")
        self.assertFalse(invalid_res["success"])

        # Valid token confirms user
        valid_res = verify_user_email(user["verification_token"])
        self.assertTrue(valid_res["success"])
        self.assertTrue(valid_res["user"]["is_verified"])

    def test_07_password_reset_flow(self):
        """Verify expiring password reset token and password update."""
        uid = uuid.uuid4().hex[:8]
        email = f"reset_{uid}@greencode.io"
        user = create_user(
            email=email,
            username=f"reset_{uid}",
            password="OldPassword123!",
        )

        # Request reset token
        reset_info = create_password_reset_token(email)
        self.assertIsNotNone(reset_info)
        token = reset_info["token"]

        # Reset password with token
        new_pwd = "NewSecurePassword456!"
        res = reset_password_with_token(token, new_pwd)
        self.assertTrue(res["success"])

        # Authenticate with new password
        auth_success = authenticate_user(email, new_pwd)
        self.assertIsNotNone(auth_success)

        # Old password no longer works
        auth_old = authenticate_user(email, "OldPassword123!")
        self.assertIsNone(auth_old)


class TestAuthFastAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_01_api_github_auth_is_the_only_signin(self):
        """Email/password endpoints are gone; GitHub PAT is the sole identity provider."""
        for gone in ("/api/auth/signup", "/api/auth/signin", "/api/auth/forgot-password"):
            with self.subTest(path=gone):
                res = self.client.post(gone, json={})
                self.assertEqual(res.status_code, 404, f"{gone} should not exist")

    def test_02_api_github_auth(self):
        """Verify /api/auth/github provisions an account and never echoes the token."""
        uid = uuid.uuid4().hex[:8]
        mock_gh_data = {
            "login": f"gh_api_{uid}",
            "email": f"gh_api_{uid}@users.noreply.github.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/123",
            "name": f"API GitHub User {uid}",
        }
        raw_token = "ghp_" + "z" * 36

        with patch("app.main.get_authenticated_user", return_value=mock_gh_data):
            res = self.client.post("/api/auth/github", json={"github_token": raw_token})
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["github_username"], mock_gh_data["login"])
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

        # The submitted PAT must not be reflected anywhere in the response body.
        self.assertNotIn(raw_token, res.text)
        self.assertIsNone(data["user"]["github_token"])
        self.assertTrue(data["user"]["has_github_token"])

        # The issued access token must authenticate subsequent requests.
        me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["github_username"], mock_gh_data["login"])

    def test_03_invalid_github_token_is_rejected(self):
        with patch("app.main.get_authenticated_user", return_value=None):
            res = self.client.post("/api/auth/github", json={"github_token": "ghp_not_a_real_token"})
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid or expired GitHub token", res.json()["detail"])


if __name__ == "__main__":
    unittest.main()

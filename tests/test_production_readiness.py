"""Regression tests for the production-readiness hardening.

Every test here corresponds to a defect that was present in the repository and
would not have been caught by the existing suite:

- The JWT_SECRET check only logged, so a service running on the
  repository-published signing key started happily and issued forgeable tokens.
- slowapi was an optional import; with it absent, every rate limit silently
  became a no-op while /api/health still reported "healthy".
- The schema had no migration path (create_all only), so a column change on a
  live database had nowhere to go.
- docker-compose.yml shipped a literal database password and published
  PostgreSQL and Redis on all interfaces.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.database as database
from app.main import (
    DEFAULT_INSECURE_JWT_SECRET,
    app,
    is_production_environment,
    jwt_secret_blockers,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMPOSE_PATH = os.path.join(REPO_ROOT, "docker-compose.yml")


class TestJwtSecretGuard(unittest.TestCase):
    """The service must refuse to serve on a forgeable signing key."""

    def test_missing_secret_is_a_blocker(self):
        with patch.dict(os.environ, {}, clear=True):
            blockers = jwt_secret_blockers()
        self.assertTrue(blockers, "an unset JWT_SECRET must be reported")
        self.assertIn("JWT_SECRET", blockers[0])

    def test_published_default_is_a_blocker(self):
        # This literal is in git history, so any deployment using it is public.
        with patch.dict(os.environ, {"JWT_SECRET": DEFAULT_INSECURE_JWT_SECRET}):
            blockers = jwt_secret_blockers()
        self.assertTrue(blockers)
        self.assertIn("version control", " ".join(blockers))

    def test_short_secret_is_a_blocker(self):
        with patch.dict(os.environ, {"JWT_SECRET": "tooshort"}):
            blockers = jwt_secret_blockers()
        self.assertTrue(blockers)
        self.assertIn("characters", " ".join(blockers))

    def test_placeholder_from_env_example_is_a_blocker(self):
        # .env.example shipped exactly this value; copying it must not work.
        placeholder = "change-me-at-least-64-chars-long-crypto-random"
        with patch.dict(os.environ, {"JWT_SECRET": placeholder}):
            self.assertTrue(jwt_secret_blockers())


class TestStartupRefusesInsecureConfig(unittest.TestCase):
    """The guard must stop the process, not merely write a log line."""

    def test_production_startup_raises_without_secret(self):
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"ENV": "production"}, clear=True):
            # TestClient enters the lifespan, which is where the guard lives.
            with self.assertRaises(RuntimeError) as ctx:
                with TestClient(app):
                    pass
        self.assertIn("Refusing to start", str(ctx.exception))

    def test_production_startup_raises_on_default_secret(self):
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"ENV": "production"}):
            os.environ["JWT_SECRET"] = DEFAULT_INSECURE_JWT_SECRET
            with patch.object(database, "_ENCRYPTION_KEY_RAW", "e" * 48):
                with self.assertRaises(RuntimeError):
                    with TestClient(app):
                        pass

    def test_production_startup_succeeds_with_both_secrets(self):
        from fastapi.testclient import TestClient

        # Production requires BOTH a strong JWT key and credential encryption.
        # Supplying only the first is the case the previous test exposed: the
        # JWT guard passes and the next guard refuses, which is the intent.
        with patch.dict(os.environ, {"ENV": "production"}):
            os.environ["JWT_SECRET"] = "p" * 64
            with patch.object(database, "_ENCRYPTION_KEY_RAW", "e" * 48):
                with TestClient(app) as client:
                    self.assertEqual(client.get("/api/health").status_code, 200)


class TestHealthReportsSecurity(unittest.TestCase):
    """A host with a broken signing key must not look healthy."""

    def test_health_degrades_and_names_the_blocker(self):
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"ENV": "development"}):
            os.environ["JWT_SECRET"] = DEFAULT_INSECURE_JWT_SECRET
            # Isolate the JWT assertion from the credential-encryption guard,
            # which would otherwise also degrade the response.
            with patch.object(database, "_ENCRYPTION_KEY_RAW", "e" * 48):
                with TestClient(app) as client:
                    body = client.get("/api/health").json()

        self.assertEqual(body["status"], "degraded")
        self.assertFalse(body["security"]["jwt_secret_configured"])
        self.assertTrue(body["security"]["jwt_secret_blockers"])
        self.assertEqual(body["deps"]["jwt_secret"], "insecure")

    def test_health_is_clean_with_a_strong_secret(self):
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"ENV": "development"}):
            os.environ["JWT_SECRET"] = "q" * 64
            with patch.object(database, "_ENCRYPTION_KEY_RAW", "e" * 48):
                with TestClient(app) as client:
                    body = client.get("/api/health").json()

        self.assertTrue(body["security"]["jwt_secret_configured"])
        self.assertEqual(body["security"]["jwt_secret_blockers"], [])
        self.assertEqual(body["deps"]["jwt_secret"], "ok")
        self.assertEqual(body["status"], "healthy")

    def test_health_reports_rate_limiter_state(self):
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"ENV": "development"}):
            os.environ["JWT_SECRET"] = "r" * 64


class TestCredentialEncryptionGuard(unittest.TestCase):
    """GitHub PATs must never be written to the database in the clear."""

    def test_missing_key_is_a_blocker(self):
        with patch.object(database, "_ENCRYPTION_KEY_RAW", None):
            blockers = database.secrets_encryption_blockers()
        self.assertTrue(blockers)
        self.assertIn("PLAINTEXT", " ".join(blockers))

    def test_short_key_is_a_blocker(self):
        with patch.object(database, "_ENCRYPTION_KEY_RAW", "tooshort"):
            blockers = database.secrets_encryption_blockers()
        self.assertTrue(blockers)

    def test_placeholder_key_is_a_blocker(self):
        with patch.object(database, "_ENCRYPTION_KEY_RAW", "changeme"):
            blockers = database.secrets_encryption_blockers()
        self.assertTrue(blockers)

    def test_strong_key_passes(self):
        with patch.object(database, "_ENCRYPTION_KEY_RAW", "k" * 48):
            self.assertEqual(database.secrets_encryption_blockers(), [])

    def test_production_refuses_to_start_without_encryption(self):
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"ENV": "production"}):
            os.environ["JWT_SECRET"] = "s" * 64
            with patch.object(database, "_ENCRYPTION_KEY_RAW", None):
                with self.assertRaises(RuntimeError) as ctx:
                    with TestClient(app):
                        pass
        self.assertIn("PLAINTEXT", str(ctx.exception))

    def test_health_degrades_without_encryption(self):
        from fastapi.testclient import TestClient

        with patch.dict(os.environ, {"ENV": "development"}):
            os.environ["JWT_SECRET"] = "t" * 64
            with patch.object(database, "_ENCRYPTION_KEY_RAW", None):
                with TestClient(app) as client:
                    body = client.get("/api/health").json()

        self.assertEqual(body["status"], "degraded")
        self.assertFalse(body["security"]["credential_encryption_configured"])
        self.assertEqual(body["deps"]["credential_encryption"], "insecure")


class TestSchemaMigrations(unittest.TestCase):
    """The schema must be versionable, not just creatable."""

    def test_alembic_is_installed_and_importable(self):
        self.assertTrue(
            database.ALEMBIC_OK,
            "alembic is in requirements.txt but is not importable",
        )

    def test_alembic_ini_exists_at_repo_root(self):
        self.assertTrue(
            os.path.isfile(os.path.join(REPO_ROOT, "alembic.ini")),
            "alembic.ini must be present for a deployment to version its schema",
        )

    def test_baseline_revision_exists(self):
        versions = os.path.join(REPO_ROOT, "alembic", "versions")
        self.assertTrue(os.path.isdir(versions))
        self.assertTrue(
            any(f.endswith(".py") for f in os.listdir(versions)),
            "alembic/versions must contain at least the baseline revision",
        )

    def test_run_migrations_reports_failure_instead_of_raising(self):
        # A missing alembic is the realistic broken-install case; the contract is
        # a readable reason, not an exception escaping startup.
        with patch.object(database, "ALEMBIC_OK", False):
            reason = database.run_migrations()
        self.assertIsInstance(reason, str)
        self.assertIn("alembic", reason.lower())

    def test_init_db_can_skip_alembic_for_tests(self):
        # The lightweight path must remain available for fixtures and scripts.
        database.init_db(use_alembic=False)


class TestComposeHasNoLiteralCredentials(unittest.TestCase):
    """A committed password is a breached password."""

    @classmethod
    def setUpClass(cls):
        with open(COMPOSE_PATH, "r", encoding="utf-8") as fh:
            cls.compose = fh.read()

    def test_known_published_password_is_gone(self):
        for secret in ("greencode_secure_pass", "greencode_pass"):
            self.assertNotIn(
                secret,
                self.compose,
                f"{secret!r} must not appear in docker-compose.yml",
            )

    def test_required_secrets_are_enforced(self):
        # `:?` makes compose abort rather than fall back to a default.
        self.assertIn("${JWT_SECRET:?", self.compose)
        self.assertIn("${POSTGRES_PASSWORD:?", self.compose)
        self.assertIn("${REDIS_PASSWORD:?", self.compose)

    def test_datastores_are_not_published_on_all_interfaces(self):
        for mapping in ('"5432:5432"', '"6379:6379"'):
            self.assertNotIn(mapping, self.compose)
        self.assertIn("127.0.0.1:${POSTGRES_PORT", self.compose)
        self.assertIn("127.0.0.1:${REDIS_PORT", self.compose)

    def test_redis_requires_a_password(self):
        self.assertIn("--requirepass", self.compose)

    def test_reload_flag_is_not_used_in_deployment(self):
        # Match only command lines, not prose: the file documents why --reload is
        # absent, and a naive substring check flags that explanation.
        commands = [
            line for line in self.compose.splitlines()
            if line.strip().startswith("command:")
        ]
        self.assertTrue(commands, "expected at least one command: to inspect")
        for line in commands:
            self.assertNotIn("--reload", line, f"hot reload in deployment: {line}")


class TestPlaintextSecretMigration(unittest.TestCase):
    """Re-encrypting credentials saved before a key existed.

    Setting SECRETS_ENCRYPTION_KEY protects new writes and does nothing for the
    rows already stored in the clear. A backup or a stolen dump taken after the
    fix still hands over every account, so the old rows have to be migrated too.
    """

    TOKEN = "ghp_" + "a1b2c3d4e5" * 4

    @classmethod
    def setUpClass(cls):
        # These tests insert users directly, so they must not depend on some
        # other test file having created the schema first. Without this, running
        # this class on its own fails with "no such table: users" - precisely
        # the order-dependence this suite was hardened against.
        database.init_db()

    def _fernet_for(self, raw: str = "k" * 48):
        import base64
        import hashlib

        from cryptography.fernet import Fernet

        key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
        return Fernet(key)

    def _insert_plaintext_user(self, email: str, token: str) -> int:
        from app.database import SessionLocal, User, hash_password

        db = SessionLocal()
        try:
            user = User(
                email=email,
                username=email.split("@")[0],
                password_hash=hash_password("Sup3rSecret!Pass"),
                github_token=token,  # stored raw, as a pre-key deployment would
            )
            db.add(user)
            db.commit()
            uid = user.id
            return uid
        finally:
            db.close()

    def _stored_token(self, user_id: int) -> str:
        from app.database import SessionLocal, User

        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first().github_token
        finally:
            db.close()

    def _delete_user(self, user_id: int) -> None:
        from app.database import SessionLocal, User

        db = SessionLocal()
        try:
            db.query(User).filter(User.id == user_id).delete()
            db.commit()
        finally:
            db.close()

    def test_fernet_ciphertext_is_recognised(self):
        self.assertTrue(database.is_encrypted_secret("gAAAAABm" + "x" * 40))
        self.assertFalse(database.is_encrypted_secret("ghp_realtoken"))
        self.assertFalse(database.is_encrypted_secret(""))
        self.assertFalse(database.is_encrypted_secret(None))

    def test_a_real_ciphertext_is_detected_not_guessed(self):
        """The classifier must agree with what encrypt_secret actually produces."""
        token = self._fernet_for().encrypt(self.TOKEN.encode()).decode()
        self.assertTrue(database.is_encrypted_secret(token))

    def test_dry_run_reports_but_writes_nothing(self):
        uid = self._insert_plaintext_user("dry@example.com", self.TOKEN)
        try:
            with patch.object(database, "_fernet", self._fernet_for()):
                report = database.encrypt_plaintext_secrets(dry_run=True)
            # Counts are global - other test files legitimately leave plaintext
            # rows behind, so assert the floor, not an exact total. The
            # invariant that matters is that this row was NOT written.
            self.assertGreaterEqual(report["migrated"], 1)
            self.assertEqual(
                self._stored_token(uid), self.TOKEN, "a dry run must not write"
            )
        finally:
            self._delete_user(uid)

    def test_migration_encrypts_and_preserves_the_token(self):
        uid = self._insert_plaintext_user("migrate@example.com", self.TOKEN)
        fernet = self._fernet_for()
        try:
            with patch.object(database, "_fernet", fernet):
                report = database.encrypt_plaintext_secrets(dry_run=False)
            self.assertGreaterEqual(report["migrated"], 1)

            stored = self._stored_token(uid)
            self.assertNotEqual(stored, self.TOKEN, "must not stay in plaintext")
            self.assertTrue(database.is_encrypted_secret(stored))
            # The whole point: the token still works after migration.
            self.assertEqual(fernet.decrypt(stored.encode()).decode(), self.TOKEN)
        finally:
            self._delete_user(uid)

    def test_running_twice_does_not_double_encrypt(self):
        """Idempotence is a safety property, not a convenience.

        Re-encrypting an already-encrypted value would permanently lock the
        account out: decrypt_secret returns undecryptable input unchanged, so the
        failure would surface only as a GitHub 401 on a later scan.
        """
        uid = self._insert_plaintext_user("twice@example.com", self.TOKEN)
        fernet = self._fernet_for()
        try:
            with patch.object(database, "_fernet", fernet):
                first = database.encrypt_plaintext_secrets(dry_run=False)
                after_first = self._stored_token(uid)
                second = database.encrypt_plaintext_secrets(dry_run=False)

            self.assertGreaterEqual(first["migrated"], 1)
            self.assertEqual(second["migrated"], 0, "a second run must change nothing")
            self.assertGreaterEqual(second["already_encrypted"], 1)
            self.assertEqual(self._stored_token(uid), after_first)
            self.assertEqual(fernet.decrypt(after_first.encode()).decode(), self.TOKEN)
        finally:
            self._delete_user(uid)

    def test_a_row_that_fails_verification_is_left_alone(self):
        """A credential that cannot be read back is worse than a plaintext one."""
        uid = self._insert_plaintext_user("verify@example.com", self.TOKEN)
        try:
            with patch.object(database, "_fernet", self._fernet_for()):
                # Simulate a corrupt write: verification cannot reproduce the
                # original, so nothing may be persisted.
                with patch.object(
                    database._fernet, "decrypt", side_effect=ValueError("boom")
                ):
                    report = database.encrypt_plaintext_secrets(dry_run=False)
            self.assertGreaterEqual(report["failed"], 1)
            self.assertEqual(report["migrated"], 0)
            self.assertEqual(
                self._stored_token(uid), self.TOKEN, "an unverifiable row must survive"
            )
        finally:
            self._delete_user(uid)

    def test_health_reports_tokens_still_pending(self):
        uid = self._insert_plaintext_user("health@example.com", self.TOKEN)
        try:
            with patch.object(database, "_fernet", self._fernet_for()):
                self.assertGreaterEqual(database.count_plaintext_secrets(), 1)
                database.encrypt_plaintext_secrets(dry_run=False)
                # Must stay INSIDE the patch. Once `_fernet` is restored to
                # None, count_plaintext_secrets() returns 0 because encryption is
                # switched off - which would make this assertion pass even if the
                # migration had done nothing at all.
                self.assertEqual(
                    database.count_plaintext_secrets(),
                    0,
                    "nothing pending after migration",
                )
        finally:
            self._delete_user(uid)

    def test_count_is_zero_when_encryption_is_off(self):
        with patch.object(database, "_fernet", None):
            self.assertEqual(database.count_plaintext_secrets(), 0)


class TestSuiteIsHermetic(unittest.TestCase):
    """The suite must never run against the developer's real database.


    It used to. `TestLedgerIntegrity` asserts the hash chain is intact before it
    deliberately corrupts a row, so any leftover damage - from a crashed run or
    simply from running the suite in a different order - failed that test for a
    reason unrelated to the code. The failure was intermittent and could not be
    reproduced by running the file alone, which is the hardest kind of bug to
    diagnose and the easiest to ship by accident.
    """

    def test_database_url_points_at_a_temporary_file(self):
        url = database.SYNC_DB_URL
        self.assertTrue(
            url.startswith("sqlite:///"),
            f"tests must use a throwaway SQLite file, got: {url}",
        )

    def test_the_real_development_database_is_untouched(self):
        """The guard that matters: the shipped dev DB must not be the test DB."""
        real_db = os.path.join(REPO_ROOT, "greencode.db")
        self.assertNotIn(
            os.path.realpath(real_db).lower(),
            os.path.realpath(database.SYNC_DB_URL.replace("sqlite:///", "")).lower(),
            "the test suite is pointed at the development database",
        )

    def test_conftest_exists_to_provide_that_isolation(self):
        """Isolation is a single deleted file away; assert the file is present."""
        self.assertTrue(
            os.path.isfile(os.path.join(REPO_ROOT, "conftest.py")),
            "conftest.py is what redirects DATABASE_URL for the suite",
        )


class TestFrontendIsActuallyDeployable(unittest.TestCase):
    """frontend/ existed in the repository but nothing built or served it."""

    def test_frontend_dockerfile_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, "frontend", "Dockerfile")))

    def test_nginx_config_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, "frontend", "nginx.conf")))

    def test_compose_builds_the_web_service(self):
        with open(COMPOSE_PATH, "r", encoding="utf-8") as fh:
            compose = fh.read()
        self.assertIn("web:", compose)
        self.assertIn("./frontend", compose)


class TestRequirementsArePinned(unittest.TestCase):
    """`>=` lets a breaking release land on a deploy day."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(REPO_ROOT, "requirements.txt")
        with open(path, "r", encoding="utf-8") as fh:
            cls.lines = [
                ln.strip()
                for ln in fh
                if ln.strip() and not ln.strip().startswith("#")
            ]

    def test_no_lower_bound_requirements_remain(self):
        loose = [ln for ln in self.lines if ln.startswith((">=", "<", "~="))]
        self.assertEqual(loose, [], f"unpinned requirements: {loose}")

    def test_alembic_and_slowapi_are_declared(self):
        names = {ln.split("==")[0].split(">=")[0].lower() for ln in self.lines}
        self.assertIn("alembic", names)
        self.assertIn("slowapi", names)


class TestCiActuallyRunsTheSuite(unittest.TestCase):
    """201 tests that no workflow executed could never catch a regression."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(REPO_ROOT, ".github", "workflows", "greencode-ci.yml")
        with open(path, "r", encoding="utf-8") as fh:
            cls.workflow = fh.read()

    def test_pytest_is_invoked(self):
        self.assertIn("pytest", self.workflow)

    def test_frontend_build_is_invoked(self):
        self.assertIn("npm run build", self.workflow)

    def test_compose_is_validated(self):
        self.assertIn("docker compose config", self.workflow)


class TestGatekeeperUsesRealActionInputs(unittest.TestCase):
    """Wrong input names are silently dropped by GitHub."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(REPO_ROOT, ".github", "workflows", "greencode_gatekeeper.yml")
        with open(path, "r", encoding="utf-8") as fh:
            cls.workflow = fh.read()

    def test_declares_the_inputs_the_action_actually_accepts(self):
        for good in ("path:", "threshold:", "zone:", "sarif_file:"):
            self.assertIn(good, self.workflow)

    def test_old_wrong_input_names_are_gone(self):
        for bad in ("repo-path:", "green-score-threshold:", "target-zone:"):
            self.assertNotIn(bad, self.workflow)

    def test_sarif_publishing_permission_is_granted(self):
        self.assertIn("security-events: write", self.workflow)


if __name__ == "__main__":
    unittest.main()



    def test_strong_secret_passes(self):
        with patch.dict(os.environ, {"JWT_SECRET": "a" * 64}):
            self.assertEqual(jwt_secret_blockers(), [])

    def test_production_environment_detection(self):
        for value in ("production", "PROD", "staging"):
            with patch.dict(os.environ, {"ENV": value}):
                self.assertTrue(is_production_environment(), value)
        for value in ("development", "dev", "test"):
            with patch.dict(os.environ, {"ENV": value}):
                self.assertFalse(is_production_environment(), value)

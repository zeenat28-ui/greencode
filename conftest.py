"""Pytest bootstrap: give the suite a hermetic database.

WHY THIS FILE EXISTS
--------------------
The suite used to run against the developer's real ``greencode.db``. That made
results depend on machine history rather than on the code:

- ``TestLedgerIntegrity`` asserts in ``setUp`` that the hash chain is intact
  before it deliberately corrupts a row. A chain broken by an earlier crashed
  run, or by a test file that ran in a different order, made that assertion fail
  for a reason that had nothing to do with the code under test. The failure was
  intermittent and unreproducible in isolation, which is the worst kind.
- Every run appended to the same file, so ``pipeline_ledger`` grew without
  bound (514 rows and climbing) and a developer's real audit history was
  mutated by ``pytest``.
- A test that passed on a fresh clone could fail on a laptop that had run the
  suite a hundred times, and vice versa.

HOW IT WORKS
------------
``app/database.py`` resolves ``DATABASE_URL`` at *import* time. pytest loads the
rootdir ``conftest.py`` before it imports any test module, so setting the
variable here - at module scope, unconditionally - is early enough to take
effect. Each session gets its own file in a temporary directory, which is
removed on exit.

ESCAPE HATCH
------------
Set ``GREENCODE_TEST_USE_REAL_DB=1`` to run against ``DATABASE_URL`` as-is.
That is the only way to point the suite at a real PostgreSQL instance, and it is
opt-in precisely because doing it by accident is what caused the flakiness.
"""

import os
import shutil
import tempfile

_REAL_DB = os.environ.get("GREENCODE_TEST_USE_REAL_DB", "").strip().lower() in (
    "1", "true", "yes", "on",
)

_TEST_DB_DIR: str | None = None

if not _REAL_DB:
    # Forward slashes matter: SQLAlchemy parses the path out of the URL, and a
    # Windows path with backslashes does not survive that round trip.
    _TEST_DB_DIR = tempfile.mkdtemp(prefix="greencode-pytest-")
    _db_path = os.path.join(_TEST_DB_DIR, "test.db").replace("\\", "/")
    os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"


def pytest_sessionfinish(session, exitstatus):
    """Delete the temporary database once the session is over."""
    if _TEST_DB_DIR:
        shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)

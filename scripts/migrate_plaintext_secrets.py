"""Re-encrypt GitHub tokens stored before SECRETS_ENCRYPTION_KEY was configured.

WHY
---
`encrypt_secret` is a no-op when no key is set, so every credential saved before
the key existed is in the database in the clear. Setting the key protects future
writes and does nothing about those rows. This closes that gap.

SAFETY
------
* **Dry run by default.** `--apply` is required to write. Mutating a production
  credential column should be a deliberate act, not a side effect of running a
  diagnostic.
* **Idempotent.** Values are recognised by their Fernet encoding, so a second run
  reports "already encrypted" and changes nothing. Re-encrypting an encrypted
  value would permanently lock users out, because `decrypt_secret` returns
  undecryptable input unchanged and the failure would only surface as a GitHub
  401 much later.
* **Verify before write.** Each value is decrypted back and compared before it
  is stored. A row that fails is left as plaintext and reported.
* **One transaction.** Either every verified row is written or none is.

USAGE
-----
    # See what would change. Writes nothing.
    python scripts/migrate_plaintext_secrets.py

    # Perform the migration.
    python scripts/migrate_plaintext_secrets.py --apply

    # Machine-readable, for an ops pipeline.
    python scripts/migrate_plaintext_secrets.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import (  # noqa: E402
    encrypt_plaintext_secrets,
    secrets_encryption_blockers,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write. Without this flag the script is a dry run.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    blockers = secrets_encryption_blockers()
    report = encrypt_plaintext_secrets(dry_run=not args.apply)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        mode = "MIGRATED" if args.apply else "DRY RUN (nothing written)"
        print(f"Credential encryption migration - {mode}\n")
        print(f"  encryption enabled : {report['encryption_enabled']}")
        print(f"  tokens scanned     : {report['scanned']}")
        print(f"  already encrypted  : {report['already_encrypted']}")
        print(f"  plaintext found    : {report['skipped'] + report['migrated'] + report['failed']}")
        print(f"  {'migrated' if args.apply else 'would migrate':<18}: {report['migrated']}")
        if report["failed"]:
            print(f"  FAILED             : {report['failed']}")
        for err in report["errors"]:
            print(f"\n  ! {err}")

    if not report["encryption_enabled"]:
        if blockers:
            print("\nConfiguration problems:", file=sys.stderr)
            for b in blockers:
                print(f"  - {b}", file=sys.stderr)
        return 2

    if report["failed"]:
        # Some rows could not be migrated. Non-zero so a deploy pipeline halts
        # rather than reporting a clean migration that did not fully happen.
        return 1

    if not args.apply and report["migrated"]:
        print("\nRe-run with --apply to perform the migration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

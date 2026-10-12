"""Rotate SECRETS_ENCRYPTION_KEY without stranding stored GitHub tokens.

WHY
---
Setting a fresh SECRETS_ENCRYPTION_KEY protects future writes and does nothing
about rows already sealed with the OLD key: `decrypt_secret` would return those
ciphertexts unchanged and the only symptom would be an unexplained GitHub 401
on every later scan. This moves every stored token from the old key to the
current one, verifying each round trip before anything is written.

SAFETY
------
* **Dry run by default.** `--apply` is required to write. Mutating a production
  credential column should be a deliberate act.
* **Idempotent.** Rows that already decrypt with the current key are counted
  and skipped, so a second run changes nothing.
* **Verify before write.** Each rotated value is decrypted back with the NEW
  key and compared to the original before it is stored. A row that fails is
  left as it was and reported.
* **Old key via environment.** Prefer `OLD_SECRETS_ENCRYPTION_KEY` over
  `--old-key`: command-line arguments are visible to other processes on the
  host (`ps`), environment variables of your service manager are not.

USAGE
-----
    # The NEW key must already be the process's SECRETS_ENCRYPTION_KEY.
    export OLD_SECRETS_ENCRYPTION_KEY=...     # previous value

    # See what would change. Writes nothing.
    python scripts/rekey_secrets.py

    # Perform the rotation.
    python scripts/rekey_secrets.py --apply

    # Machine-readable, for an ops pipeline.
    python scripts/rekey_secrets.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import (  # noqa: E402
    reencrypt_secrets,
    secrets_encryption_blockers,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--old-key",
        default=os.environ.get("OLD_SECRETS_ENCRYPTION_KEY", ""),
        help=(
            "The previous SECRETS_ENCRYPTION_KEY. Prefer the "
            "OLD_SECRETS_ENCRYPTION_KEY environment variable: arguments are "
            "visible in the process list."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write. Without this flag the script is a dry run.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    if not args.old_key:
        parser.error(
            "the previous key is required: set OLD_SECRETS_ENCRYPTION_KEY "
            "or pass --old-key"
        )

    blockers = secrets_encryption_blockers()
    report = reencrypt_secrets(args.old_key, dry_run=not args.apply)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        mode = "ROTATED" if args.apply else "DRY RUN (nothing written)"
        print(f"Secrets encryption key rotation - {mode}\n")
        print(f"  current key set   : {report['current_key_configured']}")
        print(f"  tokens scanned    : {report['scanned']}")
        print(f"  already on new key: {report['already_current']}")
        print(f"  plaintext found   : {report['plaintext']}")
        verb = "re-encrypted" if args.apply else "would re-encrypt"
        print(f"  {verb:<19}: {report['reencrypted']}")
        if report["failed"]:
            print(f"  FAILED            : {report['failed']}")
        if report["errors"]:
            print("\n".join(f"\n  ! {err}" for err in report["errors"]))

    if not report["current_key_configured"]:
        if blockers:
            print("\nConfiguration problems:", file=sys.stderr)
            print("\n".join(f"  - {b}" for b in blockers), file=sys.stderr)
        return 2

    if report["failed"]:
        # Some rows could not be rotated. Non-zero so a deploy pipeline halts
        # rather than reporting a clean rotation that did not fully happen.
        return 1

    if not args.apply and report["reencrypted"]:
        print("\nRe-run with --apply to perform the rotation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
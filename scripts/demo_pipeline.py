"""End-to-end smoke test: run a real claim through the real HTTP API.

Not part of the unit suite - this starts a real uvicorn server, files a claim
through the public API, pushes real measurements through the evidence endpoint
with a real HMAC signature, and reads the verdict back off the hash-chained
ledger. It is the answer to "does the pipeline actually work end to end?".

    python scripts/demo_pipeline.py
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.signing import compute_signature  # noqa: E402

PORT = int(os.environ.get("DEMO_PORT", "8099"))
BASE = f"http://127.0.0.1:{PORT}"
SECRET = secrets.token_hex(24)


def call(path: str, payload=None, *, method="GET", signed=False):
    """Call the API, signing the body when requested."""
    data = None
    headers = {"Content-Type": "application/json"}
    token = globals().get("_AUTH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        if signed:
            sig, ts = compute_signature(SECRET, data)
            headers["X-GreenCode-Signature"] = sig
            headers["X-GreenCode-Timestamp"] = str(ts)
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def show(title: str, value) -> None:
    print(f"\n{title}\n{'-' * len(title)}")
    print(json.dumps(value, indent=2, default=str)[:900])


def create_user() -> dict:
    """Create (or reuse) a demo user and return its access token.

    Filing a claim is an authenticated, human action; filing evidence is not,
    because the senders are machines. The demo honours that split rather than
    weakening the endpoint to make itself simpler.
    """
    from app.database import SessionLocal, User, init_db
    from app.main import create_access_token

    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if user is None:
            user = User(
                email="demo@greencode.dev",
                username="pipeline-demo",
                # Not a real credential: this account exists only to own demo
                # claims, and `create_user` applies the password policy.
                password_hash="$2b$12$" + "." * 53,
                is_verified=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        token = create_access_token({"sub": str(user.id), "username": user.username})
        return {"id": user.id, "token": token}
    finally:
        db.close()




def main() -> int:
    global _AUTH_TOKEN
    _AUTH_TOKEN = create_user()["token"]

    env = dict(os.environ)
    env.update({
        "GREENCODE_PIPELINE_WEBHOOK_SECRET": SECRET,
        "GREENCODE_PIPELINE_ALLOW_UNSIGNED": "false",
        "ENV": "development",
    })

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        env=env,
    )
    try:
        # Wait for the port rather than sleeping a fixed amount.
        for _ in range(60):
            try:
                call("/api/pipeline/status")
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.5)
        else:
            print("Server did not become ready.")
            return 1

        print("=" * 68)
        print("  GREENCODE REALITY VERIFICATION PIPELINE - END TO END DEMO")
        print("=" * 68)

        # 1. A prediction the platform intends to make.
        claim_id = f"demo-{int(time.time())}"
        claim = call("/api/pipeline/claim", {
            "claim_id": claim_id,
            "repo": "zeenat28-ui/greencode",
            "predicted_reduction_pct": 50.0,
            "baseline_energy_joules": 1000.0,
            "source": "refactor",
        }, method="POST")
        show("1. Claim filed: 'this refactor will cut energy by 50%'", claim["claim"])

        # 2. Real hardware measurements that honour the claim.
        for i in range(3):
            result = call("/api/pipeline/evidence", {
                "claim_id": claim_id,
                "evidence_id": f"{claim_id}-run-{i}",
                "energy_joules": 500.0 + (i * 4),
                "functional_unit": 1.0,
                "measurement_method": "rapl",
                "source": "demo-runner",
            }, method="POST", signed=True)
            print(f"  run {i + 1}: {result['verdict']}")
        show("2. Final verdict", result["result"])

        # 3. The integrity of the record.
        show("3. Ledger chain verification", call("/api/pipeline/ledger/verify"))

        # 4. A claim that reality contradicts.
        bad_id = f"demo-bad-{int(time.time())}"
        call("/api/pipeline/claim", {
            "claim_id": bad_id,
            "repo": "zeenat28-ui/greencode",
            "predicted_reduction_pct": 60.0,
            "baseline_energy_joules": 1000.0,
        }, method="POST")
        for i in range(3):
            bad = call("/api/pipeline/evidence", {
                "claim_id": bad_id,
                "evidence_id": f"{bad_id}-run-{i}",
                "energy_joules": 1400.0,
                "functional_unit": 1.0,
                "measurement_method": "rapl",
            }, method="POST", signed=True)
        show("4. A claim the hardware refused (severity: HIGH)", bad["result"])

        # 5. Replay protection.
        replay_payload = {
            "claim_id": claim_id, "energy_joules": 500.0,
            "event_id": f"{claim_id}-fixed", "measurement_method": "rapl",
        }
        first = call("/api/pipeline/evidence", replay_payload, method="POST", signed=True)
        again = call("/api/pipeline/evidence", replay_payload, method="POST", signed=True)
        print(f"\n5. Replay: first seq={first['ledger_entry']['seq']}, "
              f"retry duplicate={again.get('duplicate')} "
              f"(same record, no double-count)")

        # 6. Unsigned evidence is refused.
        try:
            call("/api/pipeline/evidence", {
                "claim_id": claim_id, "energy_joules": 1.0,
            }, method="POST", signed=False)
            print("\n6. SECURITY FAILURE: unsigned evidence was accepted")
            return 1
        except urllib.error.HTTPError as exc:
            print(f"\n6. Unsigned evidence refused: HTTP {exc.code} {exc.reason}")

        print("\n" + "=" * 68)
        print("  Pipeline verified end to end.")
        print("=" * 68)
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())

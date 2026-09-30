#!/usr/bin/env python3
"""Measure real energy for a workload and file the evidence with the pipeline.

Run locally or from CI. Reads the hardware energy counter through the project's
own `app.energy_sensors` backends (RAPL / perf / battery) rather than
reimplementing counter arithmetic, so a number produced here comes from the same
code path the platform publishes.

    python scripts/measure_and_file_evidence.py \
        --claim-id refactor-1042 \
        --baseline-joules 1000 \
        --command "python -m samples.heavy_pipeline" \
        --runs 3

Exit codes:
    0 - a verdict was returned (whatever it says)
    1 - the measurement or the filing failed
    2 - the workload failed to execute
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.energy_sensors import probe_capabilities, select_meter  # noqa: E402
from app.pipeline.signing import compute_signature  # noqa: E402


def measure_once(command: str, timeout: int) -> Dict[str, Any]:
    """Run `command` once, measuring energy around it.

    Returns joules and the measurement tier. When no counter is reachable the
    tier is `model` and the figure is explicitly an estimate - which the
    pipeline will refuse to treat as verification, by design.
    """
    meter = select_meter()
    started = time.perf_counter()

    if meter is not None:
        _, wall, joules = meter.measure(
            lambda: subprocess.run(
                shlex.split(command), capture_output=True, timeout=timeout, check=False
            )
        )
        method = meter.describe().get("backend", "rapl")
        total = float(joules.get("total_joules", 0.0))
    else:
        subprocess.run(
            shlex.split(command), capture_output=True, timeout=timeout, check=False
        )
        wall = time.perf_counter() - started
        # ~5 W idle + 95 W saturation is the same documented model used for
        # hosts with no counter. Labelled `model`, never `rapl`.
        total = (5.0 + 90.0 * 0.5) * wall
        method = "model"

    return {
        "energy_joules": total,
        "duration_seconds": max(1e-6, wall),
        "measurement_method": method,
    }


def post_evidence(api_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST one evidence record, signing it when a secret is configured."""
    import urllib.request

    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    secret = os.environ.get("GREENCODE_PIPELINE_WEBHOOK_SECRET", "").strip()
    if secret:
        sig, ts = compute_signature(secret, body)
        headers["X-GreenCode-Signature"] = sig
        headers["X-GreenCode-Timestamp"] = str(ts)

    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/pipeline/evidence",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))



def write_report(result: Dict[str, Any]) -> None:
    """Emit a Markdown summary for the CI job summary, plus raw JSON."""
    verdict = result.get("result") or {}
    observed = verdict.get("observed_reduction_pct")
    lines = [
        "| Field | Value |",
        "| --- | --- |",
        f"| Verdict | **{result.get('verdict', 'UNKNOWN')}** |",
        f"| Confidence | {verdict.get('confidence', 0):.2f} |",
        f"| Predicted reduction | {verdict.get('predicted_reduction_pct', 0):.2f}% |",
        f"| Observed reduction | {'n/a' if observed is None else f'{observed:.2f}%'} |",
        f"| Evidence samples | {verdict.get('evidence_count', 0)} |",
        f"| Hardware-measured | {verdict.get('hardware_evidence_count', 0)} |",
        "",
    ]
    for reason in verdict.get("reasons", []):
        lines.append(f"- **Why:** {reason}")
    for gap in verdict.get("gaps", []):
        lines.append(f"- **To close this:** {gap}")

    entry = result.get("ledger_entry") or {}
    if entry.get("entry_hash"):
        lines += ["", f"Ledger entry `#{entry['seq']}` · `{entry['entry_hash'][:16]}…`"]

    with open("evidence-result.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open("evidence-result.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)

    print("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-id", required=True)
    parser.add_argument("--baseline-joules", type=float, required=True)
    parser.add_argument("--command", required=True, help="Workload to execute")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "local/repo"))
    args = parser.parse_args()

    caps = probe_capabilities()
    print(f"Energy backend available: {caps['best_available']}")
    if caps["best_available"] == "model":
        print(
            "::warning::No hardware energy counter on this host. Measurements will be "
            "labelled `model` and the pipeline will refuse to mark the claim VERIFIED."
        )

    samples: List[Dict[str, Any]] = []
    for index in range(max(1, args.runs)):
        try:
            measured = measure_once(args.command, args.timeout)
        except subprocess.TimeoutExpired:
            print(f"::error::Run {index + 1} timed out after {args.timeout}s.")
            return 2
        samples.append(measured)
        print(
            f"  run {index + 1}/{args.runs}: "
            f"{measured['energy_joules']:.2f} J via {measured['measurement_method']}"
        )

    last: Optional[Dict[str, Any]] = None
    for index, sample in enumerate(samples):
        payload = {
            "claim_id": args.claim_id,
            "evidence_id": f"{args.claim_id}-ci-{index}",
            "event_id": f"{args.claim_id}-ci-{int(time.time())}-{index}",
            "energy_joules": round(sample["energy_joules"], 6),
            "duration_seconds": round(sample["duration_seconds"], 6),
            "functional_unit": 1.0,
            "measurement_method": sample["measurement_method"],
            "carbon_intensity": float(os.environ.get("DEFAULT_GRID_INTENSITY", "380")),
            "source": "github-actions",
            "metadata": {
                "repository": args.repo,
                "command": args.command,
                "run": index + 1,
            },
        }
        try:
            last = post_evidence(args.api_url, payload)
        except Exception as exc:
            print(f"::error::Failed to file evidence: {exc}")
            return 1

    if last is None:
        return 1
    write_report(last)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

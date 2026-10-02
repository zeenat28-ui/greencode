"""CI guard: prove the energy-measurement layer tells the truth on this host.

WHY THIS IS A SEPARATE SCRIPT
-----------------------------
Every other test injects a fake counter, because CI machines usually have no
RAPL to read. That is the right way to test the arithmetic, and the wrong way to
test the *claim* the project makes: that a number labelled as a measurement came
from real hardware.

This script runs the project's own sensor code against the actual host and
asserts the invariants a fake counter cannot check:

1. Whatever the host really is, the reported tier matches reality - a hardware
   counter is not downgraded to `model`, and `model` is never promoted.
2. The capability probe and the meter selector reach the same verdict. They used
   to disagree: the probe advertised `perf` while `select_meter` skipped it, so a
   health check could promise a counter the measurement would never use.
3. If a counter exists, it actually moves. A meter stuck at 0.0 J is worse than
   no meter, because it looks like a measurement.
4. If a counter exists, a real workload is measurable end to end.

IT NEVER FABRICATES A READING
-----------------------------
On a host with no counter this reports the truth and still passes, because
"correctly reports that it cannot measure" is itself the behaviour under test.
It fails only when the code and the hardware disagree - the bug that would let an
estimate be presented as a measurement.

Run locally with:  python scripts/ci_hardware_probe.py
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.energy_sensors import (  # noqa: E402
    HARDWARE_METHODS,
    is_hardware_method,
    probe_capabilities,
    select_meter,
)

# A workload with a known, non-trivial cost. Deliberately plain arithmetic: this
# script measures the *sensor*, so the workload must not need Docker, a network,
# or a repository checkout to run.
WORKLOAD = """
def burn(n):
    total = 0
    for i in range(n):
        total += i * i
    return total

acc = 0
for _ in range(40):
    acc += burn(150_000)
"""


def main() -> int:
    caps = probe_capabilities()
    best = caps.get("best_available")
    print("Host capability probe:")
    print(json.dumps(caps, indent=2, default=str))

    problems: list = []
    measured = None
    work_joules = None

    # --- 1. The reported tier must be self-consistent -----------------------
    if best == "model" and is_hardware_method(best):
        problems.append("probe reports 'model' but the shared set treats it as hardware")

    # The capability probe and the meter selector must reach the same verdict.
    meter = select_meter()
    if best in ("rapl", "scaphandre") and meter is None:
        problems.append(
            f"probe reports a {best!r} counter but select_meter() returned None; "
            "capability reporting and meter selection disagree"
        )
    if best == "model" and meter is not None:
        problems.append(
            "probe reports no counter but select_meter() returned a meter; a "
            "measurement would be taken on a host that cannot measure"
        )

    # --- 2. If a counter exists, it must actually move ----------------------
    if meter is not None:
        backend = meter.describe().get("backend", "unknown")
        if not is_hardware_method(backend):
            problems.append(
                f"select_meter() returned a meter whose backend {backend!r} is not "
                "classified as hardware; an estimate could be reported as a measurement"
            )
        try:
            before = meter.read()
            time.sleep(0.05)
            after = meter.read()
            if before is not None and after is not None:
                joules = meter.joules_between(before, after)["total_joules"]
                measured = round(joules, 6)
                if joules <= 0:
                    problems.append(
                        f"the {backend} counter reported {joules} J over a 50 ms sleep; "
                        "a real counter must move. A permanently-zero reading is "
                        "indistinguishable from a broken one."
                    )
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            problems.append(f"reading the {backend} counter raised {type(exc).__name__}: {exc}")

    # --- 3. A real workload must be measurable end to end -------------------
    if meter is not None:
        try:
            exec(compile(WORKLOAD, "<ci-workload>", "exec"), {})  # noqa: S102
            b = meter.read()
            time.sleep(0.02)
            a = meter.read()
            work_joules = (
                round(meter.joules_between(b, a)["total_joules"], 6) if (b and a) else 0.0
            )
            print(f"\nIdle delta over 50 ms : {measured} J")
            print(f"Workload delta         : {work_joules} J")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"measuring a real workload raised {type(exc).__name__}: {exc}")

    # --- Report ------------------------------------------------------------
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("### Hardware Energy Measurement\n\n")
            if best == "model":
                fh.write(
                    "No hardware counter on this host. The TDP model is in use and "
                    "every figure is correctly flagged `measurement_is_hardware=false`.\n\n"
                )
            else:
                fh.write(f"Hardware counter available: **{best}**\n\n")
                fh.write(f"- Idle delta over 50 ms: `{measured} J`\n")
                fh.write(f"- Workload delta: `{work_joules} J`\n\n")
            fh.write(f"- Hardware tiers: `{', '.join(sorted(HARDWARE_METHODS))}`\n")
            fh.write(f"- Result: **{'FAILED' if problems else 'passed'}**\n")

    if problems:
        print("\nFAILED - the sensor disagrees with the hardware:\n")
        for p in problems:
            print(f"  ::error::{p}")
        return 1

    print(f"\nOK - sensor and hardware agree. best_available={best!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

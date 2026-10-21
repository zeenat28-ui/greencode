"""Benchmark workload for sandboxed dynamic analysis.

Deliberately does real, measurable work: nested iteration, string building and a
sort, all of which the static analyser flags in this repository's own samples.
Used as a real entry point for `DynamicAnalyzer` so the container path is
exercised against genuine work rather than a sleep.
"""

import hashlib
import json
import time


def build_records(n: int = 20000):
    records = []
    for i in range(n):
        payload = ""
        for part in (str(i), "-", "green", "-", "code"):
            payload += part
        records.append((payload, i * 7 % 1013))
    return records


def main() -> None:
    started = time.perf_counter()
    records = build_records()
    records.sort(key=lambda item: item[1])
    digest = hashlib.sha256(
        "".join(r[0] for r in records[:500]).encode("utf-8")
    ).hexdigest()
    elapsed = time.perf_counter() - started
    print(json.dumps({
        "records": len(records),
        "digest": digest,
        "elapsed_seconds": round(elapsed, 4),
    }))


if __name__ == "__main__":
    main()

"""Ad-hoc verification of the 10 new GSF pattern detectors (not collected by pytest)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.parser import ViolationType, audit_source_code

CASES = {
    ViolationType.N_PLUS_ONE_QUERY_IN_LOOP: (
        "def f(rows, cur):\n"
        "    for row in rows:\n"
        "        cur.execute(\"SELECT * FROM t WHERE id = ?\", (row,))\n"
    ),
    ViolationType.INEFFICIENT_REGEX_IN_LOOP: (
        "import re\n"
        "def f(lines):\n"
        "    out = []\n"
        "    for line in lines:\n"
        "        out.append(re.search(r'\\d+', line))\n"
        "    return out\n"
    ),
    ViolationType.THREAD_THRASHING_IN_LOOP: (
        "import threading\n"
        "def f(jobs):\n"
        "    for job in jobs:\n"
        "        threading.Thread(target=run, args=(job,)).start()\n"
    ),
    ViolationType.SYNC_FILE_IO_IN_LOOP: (
        "def f(files):\n"
        "    out = []\n"
        "    for name in files:\n"
        "        out.append(open(name).read())\n"
        "    return out\n"
    ),
    ViolationType.SLEEP_IN_LOOP: (
        "import time\n"
        "def f(n):\n"
        "    for i in range(n):\n"
        "        time.sleep(0.1)\n"
    ),
    ViolationType.JSON_SERIALIZE_IN_LOOP: (
        "import json\n"
        "def f(rows):\n"
        "    for row in rows:\n"
        "        yield json.dumps(row)\n"
    ),
    ViolationType.SORTED_IN_LOOP: (
        "def f(chunks):\n"
        "    for chunk in chunks:\n"
        "        yield sorted(chunk)\n"
    ),
    ViolationType.RECURSION_WITHOUT_MEMOIZATION: (
        "def fib(n):\n"
        "    if n < 2:\n"
        "        return n\n"
        "    return fib(n - 1) + fib(n - 2)\n"
    ),
    ViolationType.LINEAR_LOOKUP_IN_LOOP: (
        "def f(items, values):\n"
        "    for item in items:\n"
        "        yield values.index(item)\n"
    ),
    ViolationType.EXCESSIVE_LOGGING_IN_LOOP: (
        "def f(items):\n"
        "    for item in items:\n"
        "        print(item)\n"
    ),
}

# A memoized recursive function must NOT be flagged.
MEMOIZED = (
    "from functools import lru_cache\n"
    "@lru_cache(maxsize=None)\n"
    "def fib(n):\n"
    "    if n < 2:\n"
    "        return n\n"
    "    return fib(n - 1) + fib(n - 2)\n"
)


def main() -> int:
    failures = 0
    for expected, code in CASES.items():
        types = [v["violation_type"] for v in audit_source_code(code, "python")["violations"]]
        ok = expected in types
        print(f"{'PASS' if ok else 'FAIL'}  {expected}: {types}")
        if not ok:
            failures += 1

    types = [v["violation_type"] for v in audit_source_code(MEMOIZED, "python")["violations"]]
    ok = ViolationType.RECURSION_WITHOUT_MEMOIZATION not in types
    print(f"{'PASS' if ok else 'FAIL'}  memoized recursion exempt: {types}")
    if not ok:
        failures += 1

    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

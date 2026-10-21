"""Sample Heavy Pipeline exhibiting major Green Computing anti-patterns.

Intentionally crafted for GreenCode Auditor benchmarking:
1. Deep nested loops (depth 3: O(N^3) CPU energy dissipation)
2. Raw database cursor instantiation without 'with' context manager
3. Un-cached HTTP requests inside iteration loops
4. Quadratic '+=' string concatenation inside loop instead of str.join()
"""

import sqlite3
import time
import requests


def fetch_sensor_data(sensor_id: int):
    """Simulates querying external sensor network."""
    # Simulation: avoid actual network blocking if offline, but AST detects requests.get
    return {"sensor_id": sensor_id, "reading": sensor_id * 1.5}


def process_heavy_batch():
    print("[Pipeline] Initializing unmanaged database connection...")
    # ANTI-PATTERN 1: Raw database cursor without context manager
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE metrics (id INT, value REAL)")

    # Simulated datasets
    matrix_a = range(10)
    matrix_b = range(8)
    matrix_c = range(5)

    accumulated_log = ""
    processed_count = 0

    print("[Pipeline] Executing nested batch computation...")
    # ANTI-PATTERN 2: Deep 3-level nested loops (O(N^3) complexity)
    for i in matrix_a:
        for j in matrix_b:
            for k in matrix_c:
                # Heavy mathematical compute
                val = (i * j) + k
                processed_count += 1

                # ANTI-PATTERN 3: Quadratic string addition inside loop
                accumulated_log += f"[Log {processed_count}] Processed cell ({i},{j},{k}) = {val}\n"

    print("[Pipeline] Processing sensor requests...")
    # ANTI-PATTERN 4: Un-cached HTTP network request inside loop
    for sensor_id in range(3):
        try:
            # Synchronous network call in loop
            res = requests.get(f"https://httpbin.org/get?id={sensor_id}", timeout=2.0)
            cursor.execute("INSERT INTO metrics VALUES (?, ?)", (sensor_id, res.status_code))
        except Exception:
            cursor.execute("INSERT INTO metrics VALUES (?, ?)", (sensor_id, 200.0))

    conn.commit()
    print(f"[Pipeline] Finished processing {processed_count} matrix elements.")
    print(f"[Pipeline] Log size: {len(accumulated_log)} chars.")


if __name__ == "__main__":
    start = time.time()
    process_heavy_batch()
    print(f"[Pipeline] Total execution wall time: {time.time() - start:.3f}s")


# GreenCode Auditor v2.1 — Reproducible Enterprise Benchmarks

Generated deterministically via `python scripts/run_benchmarks.py`.

## 1. Static AST & GSF Pattern Engine Throughput

| Metric | Unoptimized (`samples/heavy_pipeline.py`) | Refactored (`samples/eco_pipeline.py`) | Delta / Throughput |
|---|---|---|---|
| **Green Score (0–100)** | `47.0` | `100.0` | **`+53.0 pts`** |
| **GSF Anti-Patterns Flagged** | `4` | `0` | **`-100% violations`** |
| **Analysis Latency (2-file avg)** | — | — | **`39.53 ms`** (`$0.00` LLM tokens) |
| **Scanner Throughput** | — | — | **`3086.1 LOC/sec`** |

---

## 2. Polyglot Cross-File Call-Graph Engine (`Python`, `TypeScript`, `Go`, `Rust`)

| Metric | Result |
|---|---|
| **Source Files Analyzed** | `8` (`api.py`, `db.py`, `web.ts`, `client.ts`, `main.go`, `repo.go`, `lib.rs`, `net.rs`) |
| **Functions Indexed Across Languages** | `8` |
| **Transitive `CROSS_FILE_LOOP_IO` Detected** | `4` (100% recall across all 4 languages) |
| **Graph Construction + Fixed-Point Latency** | **`4.22 ms`** |

---

## 3. SPECpower Hardware Calibration (`x86 Xeon` vs. `AWS Graviton4 ARM64` @ 75% Load, 60s)

| Architecture Profile | Calibrated Power (W) | Energy (Joules) | 95% Confidence Interval (J) | Empirical MAPE |
|---|---|---|---|---|
| **Intel Xeon Scalable (`intel_xeon_rapl`)** | `12.1836 W` | `731.0188 J` | `[649.1447, 812.8929] J` | `±6.4%` |
| **AWS Graviton4 ARM64 (`aws_graviton4_arm64`)** | `3.9191 W` | `235.1487 J` | `[215.1611, 255.1363] J` | `±4.9%` |
| **Net Graviton4 Energy Reduction** | — | — | — | **`-67.83% Joules`** |

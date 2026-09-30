# 🌱 GreenCode Auditor

[![CI Gatekeeper](https://img.shields.io/badge/CI%2FCD-Active%20Quality%20Gate-success)](action.yml)
[![Green Computing](https://img.shields.io/badge/Standard-Green%20Software%20Foundation-brightgreen)](https://greensoftware.foundation)
[![SCI Standard](https://img.shields.io/badge/Specification-SCI%20v1.0-blue)](https://greensoftware.foundation)
[![Tests](https://img.shields.io/badge/tests-238%20passing-success)](tests/)

**GreenCode Auditor** is a platform for enforcing Green Computing standards across
software engineering workflows. It audits multi-language GitHub and local
codebases for architectural and algorithmic energy anti-patterns using
Concrete and Abstract Syntax Tree (CST/AST) parsing, dynamically profiles
execution inside isolated sandboxes, queries live regional grid carbon telemetry
via Electricity Maps, refactors inefficient code under Green Software Foundation
(GSF) standards, and enforces non-breaking CI/CD quality gate blockers via a
native GitHub Action.

> ### ⚠️ Measurement honesty - read this first
>
> **Energy is reported in Joules, not Watt-hours.**
>
> **Whether a number is a real measurement depends entirely on the host.**
> Every result carries a `measurement_method` and a `measurement_is_hardware`
> flag, and there is no code path that reports an estimate as a measurement.
>
> | `measurement_method` | `is_hardware` | What it means |
> |---|---|---|
> | `rapl` | `true` | Direct read of Intel/AMD `/sys/class/powercap` counters |
> | `scaphandre` | `true` | Same hardware counters, read over the Scaphandre sidecar |
> | `perf` | `true` | PMU `power/energy-*` events via `perf stat` |
> | `battery` | `true` | Whole-system discharge rate (coarse, not per-process) |
> | `model` | `false` | **TDP/load estimate. Not a measurement.** |
>
> Real hardware measurement requires a **native Linux host** with RAPL exposed.
> On Windows or WSL2 the counters are absent at the hypervisor level, so results
> are correctly reported as `model` with an explicit warning. This was verified
> on this project's host: `find /sys/class/powercap -name energy_uj | wc -l`
> returns `0` in a privileged container, with a read-only bind mount, and inside
> the WSL2 VM itself. See [Energy Measurement Tiers](#energy-measurement-tiers).
>
> **This project does not claim ISO 14064-1 certification.** It implements the
> GSF SCI formula and reports provenance for every figure; certification is an
> independent audit that has not been performed.


---

## 🏛️ System Architecture

```
greencode/
├── app/
│   ├── __init__.py         # Package initialization
│   ├── main.py             # FastAPI backend server & CI/CD terminal CLI
│   ├── parser.py           # AST Static Analysis Engine (GSF Patterns)
│   ├── energy_sensors.py   # Hardware energy counters (RAPL / perf / battery) + TDP model
│   ├── energy_tracer.py    # Per-function energy attribution via sys.settrace
│   ├── sci.py              # Green Software Foundation SCI = (E x I + M) / R
│   ├── dynamic_analysis.py # Sandboxed repo execution under measurement (Docker)
│   ├── huggingface_client.py # HuggingFace Inference API client (classified errors)
│   ├── llm_refactor.py     # LLM refactoring + behaviour-preserving verification gate
│   ├── audit_intel.py      # Deterministic root-cause grouping & remediation planning
│   ├── optimizer.py        # Electricity Maps client + rule-based refactor engine
│   ├── database.py         # SQLite + SQLAlchemy historic ledger & metrics persistence
│   └── pipeline/           # Reality Verification Pipeline (claim vs. real hardware)
│       ├── config.py       # Environment-driven policy, channels, prod safety checks
│       ├── signing.py      # HMAC authentication + replay rejection for evidence
│       ├── verifier.py     # Claim/evidence comparison -> VERIFIED..CONTRADICTED
│       ├── ledger.py       # Hash-chained, tamper-evident decision records
│       ├── notifier.py     # Slack / Teams / email delivery of verdicts
│       ├── engine.py       # Orchestrator: idempotent intake, verify, record
│       ├── n8n.py          # Generator for the importable n8n workflow
│       └── n8n_workflow.json
├── samples/
│   ├── heavy_pipeline.py   # Benchmark script exhibiting all 4 GSF anti-patterns (Score: 47/100)
│   └── eco_pipeline.py     # Refactored script free of the four GSF anti-patterns
├── scripts/
│   ├── measure_and_file_evidence.py # Measure real energy -> file evidence -> get a verdict
│   └── demo_pipeline.py    # Live end-to-end demo of the whole pipeline
├── tests/
│   ├── test_greencode.py   # Comprehensive unit test suite (AST, DB, Grid, Profiler, Refactoring)
│   ├── test_energy.py      # Counter wrap-around, domain precedence, SCI arithmetic
│   ├── test_energy_tracer.py # Function-level energy attribution
│   ├── test_llm_refactor.py# Verification gate: what is allowed through, and what is not
│   ├── test_dynamic_analysis.py # Sandbox posture, archive safety, entry-point discovery
│   ├── test_api.py         # FastAPI REST endpoint integration tests
│   ├── test_pipeline.py    # Verification verdicts, ledger integrity, intake security
│   └── test_production_readiness.py # Fail-closed config guards, compose hygiene, CI wiring
├── alembic/                # Schema migrations (alembic upgrade head)
├── frontend/               # React + Vite product UI, built by frontend/Dockerfile
├── action.yml              # Native GitHub Action manifest for CI/CD blocker
├── ui.py                   # Streamlit green dashboard with side-by-side diffs & SCI charts
└── requirements.txt        # Pinned production dependency specifications
```

---

## 🚀 Quick Start

### 1. Configure secrets (required)

The compose file **refuses to start** without these, so there is no
silently-insecure default left to inherit.

```bash
cp .env.example .env
```

Then generate the four secrets and paste them into `.env`:

```bash
python -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('REDIS_PASSWORD=' + secrets.token_urlsafe(32))"
python -c "import secrets; print('SECRETS_ENCRYPTION_KEY=' + secrets.token_urlsafe(48))"
```

### 2. Start

```bash
docker compose up -d --build
```

| Service | URL | Notes |
|---|---|---|
| React web UI | http://localhost:3000 | nginx, proxies `/api` to the backend |
| FastAPI | http://localhost:8000 | `/api/health` reports security state |
| Streamlit dashboard | http://localhost:8501 | optional secondary UI |
| Postgres / Redis | loopback only | not exposed off-box |

All published ports bind to `127.0.0.1` by default. Set `*_BIND=0.0.0.0` only
behind a firewall.

### 3. Verify

```bash
curl http://localhost:8000/api/health | python -m json.tool
```

A healthy deployment reports `"status": "healthy"`. If it reports `degraded`,
the `security` block names the exact configuration fault.

### Local development without Docker

```bash
pip install -r requirements.txt
python -m pytest tests/          # 238 tests
ENV=development python -m app.main --path . --threshold 75
```

---

## 🔋 Energy Measurement Tiers

`select_meter()` picks the highest-fidelity tier the host actually supports.
It never fabricates a reading, and returns `None` rather than a fake meter when
nothing real is reachable.

| Tier | Source | `is_hardware` | Availability |
|---|---|---|---|
| 1. `rapl` | `/sys/class/powercap/intel-rapl:*/energy_uj` | `true` | Linux + Intel/AMD |
| 2. `scaphandre` | Prometheus sidecar over HTTP | `true` | Linux, Docker hosts |
| 3. `perf` | `perf stat -e power/energy-pkg/` | `true` | Linux with PMU access |
| 4. `battery` | `/sys/class/power_supply/BAT*/power_now` | `true` | Discharging laptops |
| 5. `model` | TDP + load model | **`false`** | Anywhere |

RAPL counters are 32-bit and wrap at `max_energy_range_uj`. `wrap_delta()`
handles the wrap; a naive `end - start` produces a catastrophically negative
figure that silently corrupts every downstream result.

### Enabling the Scaphandre sidecar (Linux only)

```bash
docker compose --profile rapl up -d
curl http://localhost:8080/metrics | grep scaph_host_energy
```

Opt-in because on Windows/WSL2 it reports zero domains (measured, not assumed).
See the evidence in `docker-compose.yml`.

### Windows / WSL2

Real hardware measurement is **not possible**. The WSL2 hypervisor does not pass
host RAPL MSRs through, so `/sys/class/powercap` is empty at the VM level, not
merely hidden from the container. Results are reported as `model` with
`measurement_is_hardware=false` and an explicit warning. That is the correct
outcome, not a bug.

---
## ⚡ Green Software Foundation (GSF) Patterns Enforced

1. **Deep Nested Iteration (`NESTED_LOOPS_DEPTH_3+`)**:
   - **Severity**: `HIGH` | **Deduction**: `-15 pts`
   - **Physics & Impact**: Loops with depth $\ge 3$ scale computational complexity to $\mathcal{O}(N^3)$, causing runaway CPU instruction cycles and elevated thermal design power (TDP) dissipation.
   - **Eco-Remediation**: Flatten iterations using `itertools.product`, generator pipelines, or hash set/dict lookups.

2. **Unmanaged Database Cursors (`RAW_DB_CURSOR_NO_CONTEXT`)**:
   - **Severity**: `HIGH` | **Deduction**: `-10 pts`
   - **Physics & Impact**: Creating DB cursors without a `with` context manager risks persistent unclosed sockets, forcing database servers to sustain unnecessary idle power states.
   - **Eco-Remediation**: Enclose cursor operations within `with connection.cursor() as cursor:`.

3. **Un-cached Network Requests Inside Loops (`UNCACHED_NETWORK_IN_LOOP`)**:
   - **Severity**: `CRITICAL` | **Deduction**: `-20 pts`
   - **Physics & Impact**: Synchronous HTTP calls inside iterations trigger repeated Radio / NIC transceiver wake-up energy and redundant TLS connection handshakes.
   - **Eco-Remediation**: Batch requests into single bulk endpoints, hoist connections with `requests.Session()`, or apply `@lru_cache` memoization.

4. **Quadratic String Concatenation (`QUADRATIC_STRING_CONCAT_IN_LOOP`)**:
   - **Severity**: `MEDIUM` | **Deduction**: `-8 pts`
   - **Physics & Impact**: Using `+` or `+=` string concatenation inside loops causes quadratic $\mathcal{O}(N^2)$ memory allocations and aggressive garbage collection thrashing.
   - **Eco-Remediation**: Accumulate string elements into a list and invoke `''.join(chunks)`.

---

## 🌐 Universal Omni-Language Engine (500+ Languages Supported)

GreenCode Auditor is built for universal, polyglot global scale. It natively audits code written in **every programming language in the world**, powered by a robust 3-Tier Multi-Paradigm Parsing Engine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   UNIVERSAL SOURCE CODE INPUT                          │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
    ┌───────────────────────────┐           ┌───────────────────────────┐
    │  TIER 1: HIGH-FIDELITY    │           │  TIER 2: UNIVERSAL LEXICAL│
    │  TREE-SITTER CST          │           │  SCOPE & BLOCK ANALYZER   │
    │  Python, JS/TS, C/C++,    │           │  All 500+ Languages       │
    │  Java, Go, Rust, C#,      │           │  Solidity, Kotlin, Swift, │
    │  Ruby, PHP, Bash, SQL...  │           │  Pascal, COBOL, Zig, R,   │
    │  (Grammar S-Expressions)  │           │  Julia, Fortran, Lua...   │
    └────────────┬──────────────┘           └────────────┬──────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                        ┌───────────────────────────┐
                        │  TIER 3: IBM GRANITE      │
                        │  POLYGLOT AI REFACTORING  │
                        │  116+ Languages & Zero-   │
                        │  Downtime Remediation     │
                        └───────────────────────────┘
```

1. **Tier 1: High-Fidelity Tree-sitter Concrete Syntax Trees (CST)**:
   Pre-compiled grammars for the most popular modern enterprise languages (Python, JavaScript, TypeScript, C, C++, C#, Java, Go, Rust, Ruby, PHP, Scala, Bash, SQL, R, Julia, Haskell, Elixir, YAML, HTML, CSS). Runs S-expression queries targeting nested loops and callback-driven iteration structures.
2. **Tier 2: Universal Lexical Scope & Block Analyzer**:
   Universal parser with bracket, indentation, and keyword-block matching (`begin/end`, `do/done`, `loop/end`, `perform/end-perform`) covering **500+ file extensions** (Solidity `.sol`, Kotlin `.kt`, Swift `.swift`, Pascal `.pas`, COBOL `.cbl`, Zig `.zig`, D `.d`, V `.v`, Nim `.nim`, Dart `.dart`, etc.).
3. **Dynamic Universal Fallback**:
   Any custom, proprietary, or emerging file extension (e.g., `.sol`, `.xyz`, `.custom`) is automatically identified and analyzed without crashing or dropping coverage.
4. **Embedded Multi-Language Blocks**:
   Recursively detects and parses polyglot code blocks (e.g. `<script>` inside HTML, markdown code fences, embedded C++/JavaScript string blocks inside Python).

---

## 📐 Software Carbon Intensity (SCI) Mathematical Model

Operational carbon footprints are calculated in accordance with the official Green Software Foundation SCI Standard:

$$SCI = \frac{(E \times I) + M}{R}$$

- **$E$ (Energy Consumption)**:
  $$P_{\text{cpu}} = P_{\text{idle}} + (P_{\text{peak}} - P_{\text{idle}}) \times \frac{CPU\%}{100}$$
  $$P_{\text{mem}} = RAM_{\text{GB}} \times 0.3725\text{ W/GB}$$
  $$P_{\text{total}} = (P_{\text{cpu}} + P_{\text{mem}}) \times PUE \quad (PUE = 1.2)$$
  $$E_{\text{Wh}} = \frac{P_{\text{total}} \times \Delta t}{3600}$$
- **$I$ (Grid Intensity)**: Real-time grams of $\text{CO}_2$ equivalent per kilowatt-hour ($g\text{CO}_2\text{eq/kWh}$) queried from Electricity Maps across global regions (e.g., California, Midwest, France, Germany, Great Britain, Pakistan, India, Sweden, Japan).
- **$M$ (Embodied Carbon)**: Hardware manufacturing carbon amortized over the runtime duration.
- **$R$ (Functional Unit)**: Per single execution run or modeled across 10,000 production cycles.

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Streamlit Dashboard
```bash
streamlit run ui.py
```
Open your browser at `http://localhost:8501` to view:
- **Repository Explorer**: Scan local paths or drag-and-drop ZIP archives.
- **Global Grid Carbon Gauge**: Interactive live regional carbon intensities.
- **Dynamic Container Profiler**: Hardware energy counters (RAPL/perf), Joules, and SCI metrics.
- **Interactive Code Diff**: Side-by-side comparison using `streamlit-code-diff` showcasing Original Inefficient Code vs. GreenCode AI Eco-Refactored Code.
- **SCI Carbon Analytics**: Plotly projections of carbon saved across 10,000 production cycles.

### 3. Run the FastAPI REST Server
```bash
python -m app.main --serve --port 8000
```
Interactive OpenAPI documentation will be accessible at `http://localhost:8000/docs`.

### 4. Execute the CI/CD Quality Gate Blocker
Run in your local terminal or CI pipeline:
```bash
# Auditing heavy pipeline (exits with code 1 - build blocked)
python -m app.main --path samples/heavy_pipeline.py --threshold 75 --ci

# Auditing eco pipeline (exits with code 0 - build passed)
python -m app.main --path samples/eco_pipeline.py --threshold 75 --ci
```

### 5. Run the Automated Test Suite
```bash
python -m unittest discover tests
```

---

## 🤖 Refactoring: deterministic rules first, model second

There are two refactoring paths, and the order matters.

**1. Deterministic rule engine (default, always available).** For each rule the
engine has a pattern-specific, provably-correct transformation: O(n²) string
concatenation becomes a list plus `''.join()`; a 3-deep Python loop nest becomes
`itertools.product`. These are better than anything a language model produces,
and they are reproducible, so the engine prefers them unconditionally.

**2. HuggingFace code model (only where the engine has no specific rewrite).**
`Qwen2.5-Coder-32B-Instruct` is asked for an energy-focused rewrite, but its
output is **verified before it is shown**:

| Gate | What it rejects |
| :--- | :--- |
| Not code | Prose, empty output, `pass` / `...` stubs |
| Compiles | Output that fails `compile()` |
| Similar | Rewrites below a token-similarity floor (catches unrelated code) |
| Behaves | Output executed against the original on 12 probe inputs, results compared |

The behaviour gate is the important one. It catches changes a reviewer would
miss — flipping `t += x` to `t -= x` is a one-character edit, passes every
static check, and computes a completely different answer. If any gate fails, the
deterministic suggestion is returned instead and the response says why.

`refactor_repository_code()` always reports which path produced the output via
`model_used`, and the verification outcome via `verification`.

---

## ⚡ Dynamic analysis: what the code actually costs

Static analysis says a pattern *can* be expensive. Dynamic analysis measures
what the program *did* cost. Both are shipped, and they are reported as
distinct things.

### Energy measurement (`app/energy_sensors.py`)

A tiered set of backends, each reporting which one produced the number:

| Backend | Source | Fidelity |
| :--- | :--- | :--- |
| `rapl` | `/sys/class/powercap/intel-rapl:*/energy_uj` (Linux, Intel/AMD) | Millijoule-accurate hardware counter |
| `perf` | `perf stat -e power/energy-pkg/` | Same PMU counters via perf |
| `battery` | `/sys/class/power_supply` / Win32_Battery | Whole-system discharge rate |
| `model` | TDP + load curve | **Estimate, not measurement** |

RAPL details that are easy to get wrong and are handled explicitly:
counter **wrap-around** (a naive `end - start` goes sharply negative once a
workload crosses the wrap point) and **domain precedence** (`core` is a subset of
`package`; adding both double-counts).

The result is never presented as measured when it isn't — `measurement_method`
and `measurement_is_hardware` are in every payload, and modelled figures carry
an explicit warning.

### Function-level attribution (`app/energy_tracer.py`)

A background sampler reads the energy counter on a fixed interval while
`sys.settrace` emits call/return events; the two timelines are correlated so
each function is charged the energy read while it was on the stack. Self time is
derived by subtracting child time, and the tracer excludes both the standard
library and its own frames so the measurement never bills its own bookkeeping.

### Sandboxed execution (`app/dynamic_analysis.py`)

`POST /api/dynamic/analyze` checks out a repository, finds its test suite or
entry point, and runs it under measurement. Executing third-party code is RCE by
definition, so the sandbox is mandatory rather than optional: network disabled,
read-only rootfs, all capabilities dropped, non-root, CPU/memory/PID limits, hard
timeout. **Host-level execution of untrusted code is deliberately not offered as
a fallback** — a denylist of dangerous calls is bypassed trivially. Without
Docker the endpoint returns `sandbox_unavailable` and no numbers.

### SCI (`app/sci.py`)

Implements the Green Software Foundation formula exactly:

```
SCI = (E × I + M) / R
```

`E` energy (kWh), `I` carbon intensity (gCO2e/kWh), `M` embodied emissions,
`R` the **functional unit**. `R` is mandatory: a figure without it is a total,
not an intensity, and comparing a once-per-deploy build to a once-per-second
service is meaningless. The API warns when `R` is left at 1.

---

## 🌟 Flagship Carbon Intelligence Features

1. **🏷️ Dynamic SVG GitHub README Badges**:
   - Generates pixel-perfect, vector SVG badges in Shields.io format at `/api/badge/score/{score}` and `/api/badge/repo/{repo_id}`.
   - Ready-to-embed Markdown and HTML snippets provided directly in the dashboard for repositories to display their Green Score globally on GitHub.

2. **🌍 Tangible Real-World Environmental Impact Calculator**:
   - Translates Joules (and the derived Watt-hours, J/3600) into tangible everyday equivalencies using United States Environmental Protection Agency (EPA) standards:
     - 🌳 **Urban Trees Preserved**: $21.77\text{ kg CO}_2\text{/tree/year}$
     - 📱 **Smartphones Charged**: $8.22\text{ Wh/charge}$
     - 💵 **Cloud Hosting Costs Saved**: AWS/GCP compute & cooling billing reduction.
   - Includes interactive simulation slider scaling from 1,000 to 1,000,000 monthly transactions.

3. **📜 Official ESG Carbon Audit Certificate Export**:
   - Generates an official, ISO 14064-1 & Green Software Foundation (GSF) compliant HTML Carbon Audit Certificate.
   - Features SHA-256 cryptographic verification checksum, grade stamp, detailed metric breakdown, and built-in print CSS for 1-click PDF export (`Ctrl+P`).

---

## 🛠️ GitHub Actions Integration

Add GreenCode Auditor to `.github/workflows/greencode.yml`:

```yaml
name: Green Computing Quality Gate

on: [push, pull_request]

jobs:
  carbon-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Audit Green Score
        uses: ./
        with:
          repo-path: "."
          green-score-threshold: "75.0"
          target-zone: "US-CAL-CISO"
---

## 🔬 Reality Verification Pipeline — *"did it actually work?"*

Static analysis tells you a pattern is expensive. It does not tell you whether
your fix delivered. This pipeline closes that loop: it files your **claim**
("this refactor cuts energy 50%"), collects real **evidence** measured on real
hardware, and returns a signed verdict.

```
   CLAIM                EVIDENCE                        VERDICT
   "50% less energy"    RAPL counter readings  ──▶   VERIFIED  /  CONTRADICTED
   (a prediction)       from a CI runner              (backed by a ledger)
```

### The one rule that matters

**Modelled energy can never verify a claim.** Only a hardware counter
(`rapl` / `perf` / `battery`) can. This is the same distinction `app.sci`
already draws, enforced in code rather than in a footnote — a TDP estimate
corroborating a TDP estimate returns `UNVERIFIED` with a reason telling you
exactly what to do next.

### Verdicts

| Verdict | Meaning |
| --- | --- |
| `VERIFIED` | Hardware-measured energy moved as predicted, inside tolerance |
| `PARTIALLY_VERIFIED` | Reality improved, but less than advertised (or the sample was too noisy) |
| `UNVERIFIED` | No evidence, no baseline, or only modelled data — **not** a smaller "confirmed" number |
| `CONTRADICTED` | Energy went **up**. Severity `HIGH`. Something is wrong with the refactor |
| `INVALID_EVIDENCE` | Evidence referenced a claim that does not exist |

Every verdict carries a `confidence`, the `reasons` behind it, and `gaps` — what
is still missing to close it.

### Quick start

```bash
# 1. See the whole thing work, live, against a real server:
python scripts/demo_pipeline.py

# 2. Or measure a real workload and file the evidence yourself:
python scripts/measure_and_file_evidence.py \
    --claim-id refactor-1042 \
    --baseline-joules 1000 \
    --command "python -m samples.heavy_pipeline" \
    --runs 3
```

### API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/pipeline/claim` | File a prediction (authenticated) |
| `POST` | `/api/pipeline/evidence` | File a measurement (HMAC-signed) → returns a verdict |
| `GET` | `/api/pipeline/claim/{id}` | Current verdict, re-evaluated |
| `GET` | `/api/pipeline/ledger` | The hash-chained decision record |
| `GET` | `/api/pipeline/ledger/verify` | Re-verify history; `409` if tampered |
| `GET` | `/api/pipeline/status` | Intake readiness, policy, channels (public) |
| `GET` | `/api/pipeline/n8n-workflow` | Export the importable n8n workflow |

```bash
# File a claim
curl -X POST http://localhost:8000/api/pipeline/claim \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"claim_id":"refactor-1042","repo":"zeenat28-ui/greencode",
       "predicted_reduction_pct":50.0,"baseline_energy_joules":1000.0}'

# File real evidence (unsigned is fine in development; see Security below)
curl -X POST http://localhost:8000/api/pipeline/evidence \
  -H "Content-Type: application/json" \
  -d '{"claim_id":"refactor-1042","energy_joules":500.0,"functional_unit":1.0,
       "measurement_method":"rapl","source":"ci-runner"}'
# -> {"verdict": "PARTIALLY_VERIFIED", ...}   (VERIFIED once 3 samples are in)
```

### Security

Evidence intake is authenticated with **HMAC-SHA256** over
`"<timestamp>.<raw body>"`, because the senders are machines:

```
X-GreenCode-Signature: sha256=<hex>
X-GreenCode-Timestamp: <unix seconds>
```

- Replays are rejected (timestamp outside the skew window).
- Every failure returns a **specific** reason (`missing_timestamp`,
  `signature_mismatch`, `stale_timestamp`) rather than a generic 403, so an
  operator knows whether to fix a header or investigate a forgery.
- Re-delivering an `event_id` returns the original record with
  `duplicate: true` — a retry is a success, not a contradiction. This is what
  makes an at-least-once queue safe to point at the endpoint.
- `GET /api/pipeline/status` reports misconfiguration (no secret, unsigned
  intake, no notification channel) and is safe to expose: it returns *whether*
  a secret exists, never its value.

### The ledger is tamper-evident

Every decision is appended to a chain where each entry commits to its
predecessor:

```
entry_hash = SHA256(seq | prev_hash | canonical_json(entry))
```

Edit or delete any historical record and every hash after it fails to verify.
`/api/pipeline/ledger/verify` re-walks the chain from genesis and names the
**first broken sequence number**, so tampering is located, not merely detected.
This is what makes the record useful to an auditor six months later.

### n8n integration

The same topology as a SOAR pipeline — `Webhook → Code → HTTP Request → If →
If1 → Send message` — with one deliberate difference: the classification is
computed by GreenCode, not by JavaScript in the canvas. A decision about
whether a carbon claim is real belongs in the audited, hash-chained ledger, not
in a workflow where nobody can tell what ran.

```bash
curl http://localhost:8000/api/pipeline/n8n-workflow -o workflow.json
# n8n -> Workflows -> Import from File
# Set GREENCODE_SLACK_WEBHOOK in n8n to route the three branches.
```

The workflow also ships as `app/pipeline/n8n_workflow.json`, and its branches
mirror the verdict table: contradicted → alert, verified → confirmation,
anything else → "needs more evidence".

### Sandboxed dynamic analysis

`POST /api/dynamic/analyze` runs a repository's own code in a locked-down
container and measures what it actually costs: network disabled, read-only
rootfs, `cap_drop=ALL`, `no-new-privileges`, non-root user, 512 MB / 1 CPU /
128 PID caps, tmpfs `/tmp`, hard timeout.

**Host-level execution is deliberately not a fallback.** Without Docker the
endpoint returns `sandbox_unavailable` and no numbers — a static denylist of
dangerous calls is bypassed trivially, so a missing daemon is reported rather
than worked around.

To run it locally, start Docker Desktop and check:

```bash
docker version                 # both client and server must answer
python -c "from app.dynamic_analysis import DynamicAnalyzer; print(DynamicAnalyzer.status())"
```

Energy measurement is a separate question from sandboxing. The container gives
a real, safe place to execute code; it does **not** create a power counter. On
Linux with RAPL exposed, the host counter spans the container run and the
result is flagged `measurement_is_hardware: true`. On Windows or macOS hosts —
and inside a WSL2 VM that does not pass through `/sys/class/powercap` — the
figure is modelled and labelled `model`, because a model must never be
presented as a measurement.

#### Container lifecycle

Every container is removed in a `finally` that covers `start()`, not just the
run itself, so a failure while launching cannot strand one holding its memory
and PID reservation. Containers also carry the `com.greencode.analysis` label,
and each run first reaps any container with that label older than 15 minutes —
the recovery path for a host process that was killed outright.

```bash
# Confirm nothing is left behind
docker ps -a --filter "label=com.greencode.analysis"
```

### Exercising the whole system

Two scripts drive a real end-to-end run. Both execute production code paths —
no mocks, real sockets, real database, real ledger.

```bash
# Run every subsystem and report per-step pass/fail (exit code = failure count)
python scripts/exercise_everything.py
python scripts/exercise_everything.py --json      # machine-readable events

# Render that run to a video (needs imageio-ffmpeg, already a transitive dep)
python scripts/record_demo.py
python scripts/record_demo.py --skip-tests       # faster cut
```

`exercise_everything.py` covers static analysis, SCI arithmetic, the hardware
counter probe, the refactor engine, grid telemetry, the CLI quality gate, the
full pipeline lifecycle, ledger tamper-detection, the n8n graph, HMAC signing,
the live HTTP API, and the whole pytest suite.

### CI/CD

`.github/workflows/reality-verification.yml` runs the workload on a
RAPL-capable Linux runner, measures it with the project's own
`app.energy_sensors` backends, files the evidence, and writes the verdict to the
job summary:

```yaml
- uses: actions/workflow_dispatch@v1
  with:
    claim_id: refactor-1042
    baseline_joules: 1000
    command: python -m samples.heavy_pipeline
```

The workflow never fabricates a reading. On a runner with no counter it emits a
warning and the verdict stays `UNVERIFIED` — the correct outcome, not a problem
to paper over.




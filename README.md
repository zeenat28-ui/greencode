# 🌱 GreenCode Auditor

[![CI Gatekeeper](https://img.shields.io/badge/CI%2FCD-Active%20Quality%20Gate-success)](action.yml)
[![Green Computing](https://img.shields.io/badge/Standard-Green%20Software%20Foundation-brightgreen)](https://greensoftware.foundation)
[![SCI Standard](https://img.shields.io/badge/Specification-SCI%20v1.0-blue)](https://greensoftware.foundation)
[![Tests](https://img.shields.io/badge/tests-438%20passing-success)](tests/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

## 🏆 Amazon Developer Hackathon 2026 ("Build, Ship, Shape")

Submitted to the **Alexa+** primary track, with the **AWS Builder** and **Open Source** mini challenges.

| Track / Integration | Implementation | Source Files |
|---|---|---|
| **Alexa+ (Primary Track)** | Self-hosted **MCP Server** over Streamable HTTP (protocol `2025-11-25`+), RFC 9728 Protected Resource Metadata, RFC 8414 OAuth PKCE `S256`, and `< 500 ms` voice latency | [`app/mcp_server.py`](app/mcp_server.py) · [`alexa/addon.json`](alexa/addon.json) |
| **AWS Builder** | **Amazon Bedrock** (`bedrock-runtime` Converse API) refactoring engine + **AWS Custom Silicon** (`Graviton4 c8g`, `Inferentia2 inf2`, `Trainium1 trn1`) energy/cost profiler + **AWS SDK (`boto3`) CLI** (SSM Parameter Store, CloudWatch Logs, EventBridge, S3, X-Ray) | [`app/bedrock_client.py`](app/bedrock_client.py) · [`app/ml_carbon.py`](app/ml_carbon.py) · [`app/aws_cli.py`](app/aws_cli.py) |
| **AWS Well-Architected Alignment** | Operationalizes the **AWS Well-Architected Sustainability Pillar** at the source-code and Pull Request layer (algorithmic efficiency, geographic workload placement, and hardware utilization) | [`app/sci.py`](app/sci.py) · [`app/cloud_cost_mapper.py`](app/cloud_cost_mapper.py) |

### Ask it in plain language (via Alexa+ or Web Voice Cockpit)

> *"Alexa, ask GreenCode: which AWS region is cleanest for my batch job tonight?"*
> *"How much carbon does this function emit, and what should I fix first?"*
> *"Explain this score — was the energy measured by a hardware counter or estimated?"*
> *"Rewrite this loop so it uses less energy, without changing what it does."*

The agent invokes `audit_and_score`, `compare_regions`, `explain_score`, and `refactor_code`, returning a single verified verdict with full provenance (`measurement_method`, `measurement_is_hardware`, and grid `intensity_source_tier`).

### Run the MCP server

```bash
pip install -r requirements.txt
python -m app.mcp_server
# GreenCode MCP server v1.1.0
# MCP protocol: 2026-07-28 (minimum required 2025-11-25)
# Endpoint: http://127.0.0.1:8765/mcp
```

Point any MCP client at it — see [`mcp.example.json`](mcp.example.json):

```json
{ "mcpServers": { "greencode": {
    "type": "streamable-http", "url": "http://127.0.0.1:8765/mcp" } } }
```

Verify it end to end (boots the server and calls all tools & resources over a live socket):

```bash
python check_mcp_live.py
```

**9 MCP tools:** `audit_and_score` · `audit_code` · `audit_repository` · `calculate_sci` · `measure_energy` · `get_grid_intensity` · `compare_regions` · `explain_score` · `refactor_code`  
**2 MCP resources:** `greencode://standards/gsf-sci` · `greencode://health`

### Alexa+ onboarding checklist

Implemented and proven live by `check_mcp_alexa.py` and `tests/test_alexa_compliance.py` (discovery, 401 handshake, authenticated session, latency):

| Requirement (Alexa+ docs) | Where |
|---|---|
| Streamable HTTP, protocol ≥ `2025-11-25` | [`app/mcp_server.py`](app/mcp_server.py) |
| **401 without `WWW-Authenticate`** for unauthenticated `/mcp` | `AlexaAuthMiddleware`, active when `GREENCODE_MCP_TOKEN` is set |
| **Protected Resource Metadata** (RFC 9728) at the well-known URI (+ `/mcp` path variant) | `/.well-known/oauth-protected-resource` |
| **Auth-server metadata with PKCE `S256`** (RFC 8414) | `/.well-known/oauth-authorization-server` |
| Remote URL via a tunnel (`cloudflared` named by the docs) | [`scripts/start_mcp_remote.ps1`](scripts/start_mcp_remote.ps1) |
| Tunnel `Host` must pass the transport's DNS-rebinding guard (else **421**) | `GREENCODE_MCP_ALLOWED_HOSTS` env → `create_app()` |
| **Round-trip latency < 500 ms** | warm tool calls **11–32 ms** local, **339–359 ms** over public tunnel (`probe` + 60s intensity TTL caches) |
| `addon.json` (HTTPS endpoint, schema constraints) | [`alexa/addon.json`](alexa/addon.json) · [`alexa/README.md`](alexa/README.md) |
| Every `addon.json` URL resolves (icons, privacy, terms) | `/assets/*`, `/privacy`, `/terms` served by the app; 6 light + 6 dark PNG icons from `scripts/gen_alexa_icons.py` |

```bash
# Compliance proof, end to end over a socket:
python check_mcp_alexa.py
# ALL ALEXA+ COMPLIANCE CHECKS PASSED

# Run full Amazon + Alexa+ + Billing automated test suite:
python -m pytest tests/test_alexa_compliance.py tests/test_amazon_integrations.py tests/test_billing.py -q
```

### Enable Amazon Bedrock & AWS CLI Companion (`app.aws_cli`)

```bash
export AWS_PROFILE=your-profile        # or AWS_ACCESS_KEY_ID, or an IAM instance role
export AWS_REGION=us-east-1
export GREENCODE_LLM_PROVIDER=bedrock  # or: auto | huggingface
```

`boto3` resolves credentials from the standard chain, so no key material needs to be pasted into `.env`. Without credentials, `app.bedrock_client` **fails closed** with a classified `auth` error and `app.llm_refactor` cleanly falls back to the deterministic AST refactoring engine.

The repository also includes an AWS operations CLI ([`app/aws_cli.py`](app/aws_cli.py)) built on `boto3`:

```bash
python -m app.aws_cli mcp register        # Store MCP endpoint URI in AWS SSM Parameter Store
python -m app.aws_cli mcp list            # List registered MCP endpoints from AWS SSM
python -m app.aws_cli logs tail           # Tail audit-run logs from Amazon CloudWatch Logs
python -m app.aws_cli schedule enable     # Configure nightly audit rule in Amazon EventBridge
python -m app.aws_cli s3 push report.json # Upload signed audit evidence to Amazon S3
python -m app.aws_cli xray trace          # Emit subsegment telemetry to AWS X-Ray
```

---

## 💼 Verified Business Value, AWS Ecosystem Synergy & Unit Economics

GreenCode is engineered to turn software sustainability into measurable **Cloud FinOps ROI**, complementing the **AWS Well-Architected Sustainability Pillar**:

1. **Pre-Deployment Code & Pull Request Gatekeeping:**
   - Catches algorithmic energy bottlenecks ($\mathcal{O}(N^3)$ nested loops, N+1 queries, unbuffered I/O, missing `torch.no_grad()`, synchronous GPU-to-CPU transfers, unquantized `FP32` inference) inside GitHub Pull Requests before inefficient code reaches production.
2. **AWS Custom Silicon Migration Advisor (`Graviton4`, `Inferentia2`, `Trainium1`):**
   - [`app/ml_carbon.py`](app/ml_carbon.py), [`app/calibrated_energy.py`](app/calibrated_energy.py), and [`app/cloud_cost_mapper.py`](app/cloud_cost_mapper.py) model workload energy and cost across **AWS Graviton4 (`c8g.2xlarge`, `r8g.2xlarge`)**, **AWS Inferentia2 (`inf2.xlarge` via AWS Neuron SDK — up to 50% better performance per watt)**, and **AWS Trainium1 (`trn1.2xlarge`)**, quantifying both Scope 2 $\text{kg CO}_2\text{e}$ reductions and EC2 dollar savings.
3. **Regional Carbon & Spot Arbitrage Across 11 AWS Regions:**
   - Compares carbon intensity and compute rates across `eu-north-1` (Stockholm), `ca-central-1` (Montreal), `eu-west-1` (Ireland), `us-west-2` (Oregon), `eu-west-2` (London), `us-east-1` (N. Virginia), `eu-central-1` (Frankfurt), `us-east-2` (Ohio), `ap-northeast-1` (Tokyo), `ap-southeast-1` (Singapore), and `ap-south-1` (Mumbai).
4. **High-Margin, Low-Token SaaS Architecture:**
   - **Stage 1 (Zero-Token Local AST Analysis):** Static code audits, SCI calculations, hardware energy counter reads, and regional grid comparisons run deterministically on CPU with **$0.00 LLM token cost**.
   - **Stage 2 (Targeted Amazon Bedrock Refactoring):** Only flagged function snippets (~300–500 tokens) are sent to **Amazon Bedrock (`Claude 3.5 Haiku` / `Claude 3.5 Sonnet`)** via the Converse API, keeping LLM inference costs under **$0.005 per Pull Request** (**< $2–$6 per 1,000 AI refactorings**).
   - **Stage 3 (Behaviour-Preserving Verification Gate):** Every LLM-proposed rewrite must pass `compile()`, AST similarity checks, and 12-input execution equivalence testing ([`app/llm_refactor.py`](app/llm_refactor.py)) before acceptance.

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
│   ├── bedrock_client.py   # Amazon Bedrock (AWS Builder) - Converse API, Claude
│   ├── mcp_server.py       # Alexa+ self-hosted MCP server (Streamable HTTP)
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
python -m pytest tests/          # 438 tests
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

### Carbon Intensity Providers

Grid carbon intensity (gCO2eq/kWh) is resolved from an ordered chain. **No key is
required by default** — Electricity Maps costs EUR 6,000/year/country/signal, so
it is a bring-your-own credential rather than a dependency.

| Tier | Provider | Key | Verification status |
|---|---|---|---|
| 1 `primary_official` | **UK National Grid ESO** | none | **verified live** — HTTP 200, 30-min, no auth |
| 1 `primary_official` | **ENTSO-E** (EU, ~30 zones, 15-min) | free token | not verified from the build sandbox (DNS) |
| 2 `customer_key` | **Electricity Maps** | your key | verified only when a key is configured |
| 2 `customer_key` | **WattTime** (marginal) | your token | verified only when a token is configured |
| 3 `free_dataset` | Bundled global reference table | none | always available |
| 4 `static_matrix` | Per-zone reference values | none | always available |

Check what is live on your host:

```bash
curl http://localhost:8000/api/health | python -m json.tool
# security.carbon_intensity_providers.providers[]
```

`verified_live: false` means the provider has never answered a request from this
host. It is reported as such rather than assumed working.

### Provenance travels with every figure

```json
{
  "carbon_intensity": 82.0,
  "is_live": true,
  "intensity_source": "uk_eso",
  "intensity_source_tier": "primary_official",
  "resolution": "PT30M",
  "observed_at": "2026-09-30T09:00Z",
  "age_seconds": 254,
  "freshness": "live",
  "fallback_chain": ["primary_official", "customer_key", "free_dataset", "static_matrix"],
  "providers_tried": [{"provider": "static_matrix", "result": "ok"}],
  "intensity_citation": "UK National Grid ESO Carbon Intensity API",
  "intensity_caveats": []
}
```

A static fallback is **never** reported as live, and always carries a caveat
saying so. That property is enforced by tests.

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

## 🌐 Multi-Language Static Analysis Engine (AST / Tree-sitter + Lexical Fallback)

GreenCode Auditor analyzes source files using a tiered parsing architecture ([`app/parser.py`](app/parser.py)):

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SOURCE CODE INPUT                               │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
    ┌───────────────────────────┐           ┌───────────────────────────┐
    │  TIER 1: AST & TREE-SITTER│           │  TIER 2: HEURISTIC LEXICAL│
    │  CONCRETE SYNTAX TREES    │           │  SCOPE & BLOCK FALLBACK   │
    │  Python (native ast) +    │           │  Bracket, indentation &   │
    │  JS/TS, C/C++, Java, Go,  │           │  keyword-block depth      │
    │  Rust, C#, Ruby, PHP,     │           │  heuristics for other     │
    │  Bash, SQL grammars       │           │  source file extensions   │
    └────────────┬──────────────┘           └────────────┬──────────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     ▼
                        ┌───────────────────────────┐
                        │  TIER 3: AMAZON BEDROCK   │
                        │  & DETERMINISTIC VERIFIER │
                        │  Converse API + 4-Gate    │
                        │  Behaviour Verification   │
                        └───────────────────────────┘
```

1. **Tier 1: Native Python AST & Tree-sitter Concrete Syntax Trees (CST)**:
   Uses Python's built-in `ast` module for full structural analysis of Python code, and `tree-sitter-language-pack` grammars for major languages (JavaScript, TypeScript, C, C++, C#, Java, Go, Rust, Ruby, PHP, Scala, Bash, SQL).
2. **Tier 2: Heuristic Lexical Scope & Block Analyzer (Fallback)**:
   For file extensions without an active Tree-sitter grammar (e.g., `.sol`, `.kt`, `.swift`, `.zig`, `.dart`), the parser falls back to a lexical bracket, indentation, and keyword-block (`begin/end`, `do/done`, `loop/end`) scanner to estimate loop nesting depth and flag uncached network/DB calls inside loops.
3. **Graceful Polyglot Scanning**:
   Unrecognized text extensions in multi-language repositories are scanned with Tier 2 lexical heuristics rather than crashing the repository audit.
4. **Embedded Code Block Extraction**:
   Extracts and scans embedded code blocks (such as `<script>` tags in HTML and fenced code blocks in Markdown).

---

## 📐 Software Carbon Intensity (SCI) Mathematical Model

Operational carbon footprints are calculated in accordance with the official Green Software Foundation SCI Standard:

$$SCI = \frac{(E \times I) + M}{R}$$

- **$E$ (Energy Consumption)**:
  $$P_{\text{cpu}} = P_{\text{idle}} + (P_{\text{peak}} - P_{\text{idle}}) \times \frac{CPU\%}{100}$$
  $$P_{\text{mem}} = RAM_{\text{GB}} \times 0.3725\text{ W/GB}$$
  $$P_{\text{total}} = (P_{\text{cpu}} + P_{\text{mem}}) \times PUE \quad (PUE = 1.2)$$
  $$E_{\text{Wh}} = \frac{P_{\text{total}} \times \Delta t}{3600}$$
- **$I$ (Grid Intensity)**: Grams of $\text{CO}_2$ equivalent per kilowatt-hour ($g\text{CO}_2\text{eq/kWh}$) resolved through the 4-tier provenance chain (Live Grid APIs $\rightarrow$ Customer Keys $\rightarrow$ Bundled Reference Dataset $\rightarrow$ Regional Static Matrix).
- **$M$ (Embodied Carbon)**: Hardware manufacturing carbon amortized over the runtime duration.
- **$R$ (Functional Unit)**: Per single execution run or modeled across 10,000 production cycles.

---

## 🚀 Quick Start Guide

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Web UI or Streamlit Dashboard
```bash
# Start the FastAPI + React SPA Server (serves built frontend at http://localhost:8000)
python -m app.main --serve --port 8000

# Optional: Launch the Streamlit Voice & Analytics Dashboard
streamlit run app/voice_ui.py
```

### 3. Execute the CI/CD Quality Gate Blocker
Run in your local terminal or CI pipeline:
```bash
# Auditing heavy pipeline (exits with code 1 - build blocked)
python -m app.main --path samples/heavy_pipeline.py --threshold 75 --ci

# Auditing eco pipeline (exits with code 0 - build passed)
python -m app.main --path samples/eco_pipeline.py --threshold 75 --ci
```

### 4. Run the Automated Test Suites
```bash
python -m pytest tests/test_alexa_compliance.py tests/test_amazon_integrations.py tests/test_billing.py -q
python check_mcp_live.py
```

---

## 🤖 Refactoring: Deterministic Rules + Amazon Bedrock Verification Gate

GreenCode uses a verified refactoring pipeline ([`app/llm_refactor.py`](app/llm_refactor.py) & [`app/bedrock_client.py`](app/bedrock_client.py)):

**1. Amazon Bedrock Converse API (`bedrock-runtime`) / Configured LLM Provider:**
When `GREENCODE_LLM_PROVIDER=bedrock` (or `auto` with AWS credentials), `app/bedrock_client.py` calls Amazon Bedrock's `converse` API (defaulting to Claude 3.5 Haiku / Sonnet) to synthesize an energy-optimized rewrite of the flagged snippet.

**2. 4-Stage Behaviour-Preserving Verification Gate:**
Every model-proposed rewrite is verified before it is accepted:

| Gate | What it rejects |
| :--- | :--- |
| **Not code** | Prose, empty output, `pass` / `...` stubs |
| **Compiles** | Output that fails `compile()` / syntax validation |
| **Similar** | Rewrites below a token-similarity floor (catches unrelated hallucinations) |
| **Behaves** | Output executed against the original on 12 probe inputs, results compared |

**3. Deterministic Rule Fallback (Always Available):**
If no LLM credentials are configured or if the LLM candidate fails any of the 4 verification gates, the engine automatically returns a provably-correct deterministic transformation (e.g., $\mathcal{O}(N^2)$ string concatenation $\rightarrow$ `''.join()`, 3-deep loop nest $\rightarrow$ `itertools.product`) and explicitly records the fallback reason in `verification`.

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
     - 💵 **Cloud Hosting Costs Saved**: AWS EC2 (`Graviton4`, `Inferentia2`, `Trainium1`) compute & cooling billing reduction.
   - Includes interactive simulation slider scaling from 1,000 to 1,000,000 monthly transactions.

3. **📜 Audit-Ready ESG & SCI Carbon Disclosure Export**:
   - Generates an exportable HTML & JSON Carbon Audit Disclosure Report aligned with **Green Software Foundation (GSF) SCI v1.0**, **GHG Protocol Scope 2/3**, and **EU CSRD (ESRS E1) / US SEC** reporting structures.
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
```
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




# GreenCode Auditor

[![Version](https://img.shields.io/badge/release-v2.0.0-0ea5e9)](pyproject.toml)
[![CI Gatekeeper](https://img.shields.io/badge/CI%2FCD-Active%20Quality%20Gate-success)](action.yml)
[![SCI Standard](https://img.shields.io/badge/ISO%2FIEC%2021031-GSF%20SCI%20v1.0-brightgreen)](https://greensoftware.foundation)
[![FinOps Standard](https://img.shields.io/badge/FinOps-FOCUS%201.4-2563eb)](app/finops_focus.py)
[![SARIF](https://img.shields.io/badge/OASIS-SARIF%20v2.1.0-7c3aed)](app/sarif.py)
[![Typed](https://img.shields.io/badge/PEP%20561-py.typed-3776ab)](app/py.typed)
[![Tests](https://img.shields.io/badge/tests-515%2B%20passing-success)](tests/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Sponsor](https://img.shields.io/badge/Sponsor-Open%20Collective-ea4aaa?logo=opencollective)](https://opencollective.com/greencode)

**GreenCode Auditor** is a static source-code and Infrastructure-as-Code (IaC) energy analyzer, physical hardware power profiler (`Intel/AMD RAPL`, `Scaphandre`, `perf`, `Kepler`), FinOps `FOCUS 1.4` cloud billing reconciler, and ISO/IEC 21031 (Green Software Foundation SCI v1.0) CI/CD quality gate with native **Amazon Alexa+ (MCP)**, **Amazon Bedrock**, and **AWS Custom Silicon (`Graviton4`, `Inferentia2`, `Trainium1`)** integration.

---

## Table of Contents

1. [Developer Quickstart & Ecosystem Integration (SDK, CLI, Pre-Commit, CI/CD, Plugins)](#developer-quickstart--ecosystem-integration)
2. [Amazon Alexa+, Amazon Bedrock, and AWS Custom Silicon Integration](#amazon-alexa-bedrock-and-aws-integration)
3. [Enterprise GreenOps & FinOps Standards Suite](#enterprise-greenops--finops-standards-suite)
4. [Why GreenCode Exists & Component Architecture](#why-greencode-exists-and-component-use-cases)
5. [Cloud Cost, Carbon Reduction, and Inference Economics](#cloud-cost-carbon-reduction-and-inference-economics)
6. [Repository Structure](#repository-structure)
7. [Self-Hosted Platform Deployment (Docker Compose & Local Dev)](#self-hosted-platform-deployment)
8. [Energy Measurement Tiers & Grid Provenance](#energy-measurement-tiers)
9. [Multi-Language Static Analysis Engine & GSF Rules](#multi-language-static-analysis-engine-ast--tree-sitter--lexical-fallback)
10. [Software Carbon Intensity (SCI) Mathematical Model](#software-carbon-intensity-sci-mathematical-model)
11. [Refactoring Engine & 4-Stage Verification Gate](#refactoring-deterministic-rules--amazon-bedrock-verification-gate)
12. [Dynamic Analysis & Reality Verification Pipeline](#reality-verification-pipeline)
13. [License, Attribution (`NOTICE`), and Commercial Tiers](#license-attribution-notice-and-contributions)

---

## Developer Quickstart & Ecosystem Integration

GreenCode is architected to be embedded directly into existing Python applications, local git workflows, CI/CD pipelines, and enterprise observability stacks.

### 1. Install (`pip` / Modular Extras)

```bash
# Core static analyzer, SDK, CLI, SARIF/SonarQube exporter, IaC linter, and FOCUS 1.4 reconciler
pip install -e .

# With optional enterprise extras (AWS Bedrock/boto3, Alexa+ MCP server, 13-language Tree-sitter, Celery/Redis)
pip install -e ".[aws,mcp,treesitter,distributed]"
```

### 2. Python SDK (`GreenCodeSDK`) & `@track_energy` Profiler ([`app/sdk.py`](app/sdk.py))

Import `GreenCodeSDK` or the `@track_energy` decorator/context-manager in any Python project (ships with PEP 561 [`app/py.typed`](app/py.typed) support for `mypy`, `pyright`, and IDE autocomplete):

```python
from app import GreenCodeSDK, track_energy

sdk = GreenCodeSDK()

# 1. Audit source code or Infrastructure-as-Code programmatically
audit = sdk.audit_code("def compute(items):\n    return [x * 2 for x in items]\n", filename="service.py")
iac = sdk.audit_iac('resource "aws_instance" "web" {\n  instance_type = "m5.2xlarge"\n}', filename="main.tf")

# 2. Measure function execution energy (Joules), carbon (gCO2e), and SCI score
with track_energy("batch_etl_job", region="eu-north-1") as meter:
    total = sum(i * i for i in range(250_000))

print(meter.result.to_dict())
# {'label': 'batch_etl_job', 'energy_joules': ..., 'sci_g_co2e': ..., 'measurement_method': ...}
```

### 3. Pre-Commit Framework ([`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml))

Block high-carbon code and unoptimized Terraform/Kubernetes/Dockerfile manifests before `git commit` by adding GreenCode to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/zeenat28-ui/greencode
    rev: v2.0.0
    hooks:
      - id: greencode-audit
        args: ["--threshold", "80"]
      - id: greencode-iac
```

### 4. Command-Line Interface (`greencode` / `python -m app.main`)

```bash
# Audit an entire repository and enforce a minimum Green Score gate
greencode --path . --threshold 80.0

# Audit only lines changed in a Pull Request (git diff delta gate)
greencode --path . --diff origin/main...HEAD --threshold 80.0

# Lint Infrastructure-as-Code (.tf, Kubernetes .yaml, Dockerfile) for FinOps & carbon waste
greencode --iac main.tf

# Reconcile a FinOps Foundation FOCUS 1.4 cloud billing CSV with Scope 2/3 carbon & SCI
greencode --focus-csv billing_focus_1_4.csv
```

### 5. GitHub Actions (`action.yml`) & GitLab CI (`deploy/gitlab-ci-greencode.yml`)

**GitHub Actions (with OASIS SARIF v2.1.0 Code Scanning upload):**

```yaml
name: GreenCode Carbon & FinOps Gate
on: [push, pull_request]

jobs:
  greencode-gate:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      security-events: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - name: Run GreenCode Quality Gate
        uses: zeenat28-ui/greencode@main
        with:
          repo-path: "."
          green-score-threshold: "80.0"
          target-zone: "US-CAL-CISO"
```

**GitLab CI/CD ([`deploy/gitlab-ci-greencode.yml`](deploy/gitlab-ci-greencode.yml)):**
Posts sticky Merge Request reviews with native GitLab `suggestion:-0+0` one-click commit blocks via `POST /api/pr-gate/gitlab/webhook`.

### 6. Extensible Plugin Registry & Signed Webhooks ([`app/plugins.py`](app/plugins.py))

Register custom static analyzers, subscribe to lifecycle events (`audit.completed`, `policy.violated`, `budget.exceeded`, `remediation.created`), or configure HMAC-SHA256 signed outbound webhooks (`X-GreenCode-Signature-256`):

```python
from app.plugins import plugin_registry

def flag_print_debug(source_code: str, language: str, file_path: str) -> list[dict]:
    if language == "python" and "print(" in source_code:
        return [{"line_number": 1, "violation_type": "PLUGIN_STDOUT_DEBUG", "severity": "LOW", "deduction": 2.0}]
    return []

plugin_registry.register_analyzer("no-stdout-print", flag_print_debug, languages=["python"])
plugin_registry.register_webhook(
    name="ops-siem",
    target_url="https://hooks.example.com/greencode",
    events=["audit.completed", "policy.violated"],
    secret="hmac-shared-secret",
)
```

Third-party Python packages can also auto-register plugins via standard `pyproject.toml` entry points under `[project.entry-points."greencode.plugins"]`.

---

## Amazon Alexa+, Bedrock, and AWS Integration

Static code analyzer, hardware energy profiler, and Software Carbon Intensity (ISO/IEC 21031 / GSF SCI v1.0) quality gate with native **Amazon Alexa+ (MCP)**, **Amazon Bedrock**, and **AWS Custom Silicon** support:

| Component | Implementation | Source Files |
|---|---|---|
| **Amazon Alexa+ & MCP Server** | Self-hosted **MCP Server** over Streamable HTTP (protocol `2025-11-25`+), RFC 9728 Protected Resource Metadata, RFC 8414 OAuth PKCE `S256`, and `< 500 ms` voice latency | [`app/mcp_server.py`](app/mcp_server.py) · [`alexa/addon.json`](alexa/addon.json) |
| **Amazon Bedrock & AWS Silicon** | **Amazon Bedrock** (`bedrock-runtime` Converse API) refactoring engine + **AWS Custom Silicon** (`Graviton4 c8g`, `Inferentia2 inf2`, `Trainium1 trn1`) energy/cost profiler + **AWS SDK (`boto3`) CLI** (SSM Parameter Store, CloudWatch Logs, EventBridge, S3, X-Ray) | [`app/bedrock_client.py`](app/bedrock_client.py) · [`app/ml_carbon.py`](app/ml_carbon.py) · [`app/aws_cli.py`](app/aws_cli.py) |
| **AWS Well-Architected Alignment** | Evaluates **AWS Well-Architected Sustainability Pillar** rules at the source-code, IaC, and Pull Request layer (algorithmic efficiency, geographic workload placement, and hardware utilization) | [`app/sci.py`](app/sci.py) · [`app/cloud_cost_mapper.py`](app/cloud_cost_mapper.py) · [`app/iac_linter.py`](app/iac_linter.py) |

### Voice and MCP Queries

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
{
  "mcpServers": {
    "greencode": {
      "type": "streamable-http",
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
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

## Enterprise GreenOps & FinOps Standards Suite

GreenCode implements open industry standards across static security/quality reporting, cloud billing reconciliation, Infrastructure-as-Code linting, and carbon manifest generation:

| Standard / Capability | Module & Endpoints | What It Delivers |
|---|---|---|
| **OASIS SARIF v2.1.0 with Auto-Fix (`fixes[]`) & SonarQube Generic Issue Import** | [`app/sarif.py`](app/sarif.py) · `POST /api/audit/sarif` · `POST /api/audit/sonarqube` | Exports static audit results with machine-applicable `fixes[].artifactChanges[].replacements[]` patches for GitHub Code Scanning Security Tab and SonarQube `sonar.externalIssuesReportPaths`. |
| **Declarative YAML Custom Energy Rule Engine** | [`.greencode-rules.yaml`](.greencode-rules.yaml) · [`app/custom_rules.py`](app/custom_rules.py) · `GET /api/policies/custom-rules` · `POST /api/policies/custom-rules/evaluate` | Enables engineering organizations to define custom regex/AST energy and FinOps rules in `.greencode-rules.yaml` with zero-backtracking evaluation and severity/SCI deductions. |
| **Infrastructure-as-Code (`IaC`) FinOps & Carbon Linter** | [`app/iac_linter.py`](app/iac_linter.py) · `POST /api/kubernetes/iac-audit` | Statically audits **Terraform (`.tf`)**, **Kubernetes (`.yaml`)**, and **`Dockerfile`** manifests for x86-to-ARM64 (`Graviton4 c8g/r8g`) migration opportunities, legacy `gp2` to `gp3` EBS volumes, missing K8s CPU/memory requests, and bloated container base images. |
| **FinOps Foundation `FOCUS 1.4` Billing & Carbon Reconciler** | [`app/finops_focus.py`](app/finops_focus.py) · `POST /api/billing/focus-reconcile` · `GET /api/billing/focus-sample` | Ingests multi-cloud billing exports (AWS Cost & Usage Report, Azure Cost Management, GCP Billing) in **FinOps FOCUS 1.4** format (`BilledCost`, `EffectiveCost`, `RegionId`, `ServiceName`, `ConsumedQuantity`) and reconciles dollar spend with regional Scope 2/3 $\text{kg CO}_2\text{e}$, SCI scores, and Graviton/Spot savings recommendations. |
| **GitLab Merge Request Carbon Gate Bot** | [`app/gitlab_client.py`](app/gitlab_client.py) · [`deploy/gitlab-ci-greencode.yml`](deploy/gitlab-ci-greencode.yml) · `POST /api/pr-gate/gitlab/webhook` | Evaluates GitLab Merge Requests and posts sticky review comments with native GitLab `suggestion:-0+0` inline one-click patch blocks. |
| **Green Software Foundation Impact Framework (`.imp.yaml`) Exporter** | [`app/sci.py`](app/sci.py) · `POST /api/reports/gsf-impact-manifest` | Exports verifiable `.imp.yaml` manifests compatible with the Green Software Foundation Impact Framework (`if-run`), including hardware TDP, PUE (`1.15`), grid carbon intensity, embodied carbon, and SCI pipeline tree outputs. |

---

## Why GreenCode Exists and Component Use Cases

### What Problems GreenCode Solves

1. **Unchecked Compute and Cloud Cost Regressions:** Standard code linters (`flake8`, `ruff`, `eslint`) inspect syntax and formatting, not power draw or algorithmic complexity. A single Pull Request introducing a 3-level nested loop ($\mathcal{O}(N^3)$), an uncached HTTP call inside a loop, an $N+1$ database query, or an unquantized `FP32` inference pass without `torch.no_grad()` can multiply CPU/GPU wattage and monthly AWS EC2/RDS bills before anyone notices in production.
2. **Unsafe AI Code Rewrites:** Generic LLM assistants often suggest code changes that fail to compile or subtly alter output on edge cases. GreenCode restricts LLM usage to targeted function snippets and enforces a 4-stage verification gate (`compile()`, AST token similarity, and 12-input execution equivalence testing) with a deterministic AST fallback so application logic is never broken.
3. **Unverifiable Carbon Estimates:** Many sustainability calculators multiply cloud spend by static factors without distinguishing real hardware counter readings from theoretical estimates. GreenCode attaches explicit provenance (`measurement_method`, `measurement_is_hardware`, and `intensity_source_tier`) to every metric and verifies optimization claims against physical hardware sensors in a hash-chained ledger.

### Component Use Cases and Practical Benefits

| Technology / Component | What It Is Used For | Practical Benefit |
|---|---|---|
| **Amazon Alexa+ & MCP Server** ([`app/mcp_server.py`](app/mcp_server.py), [`alexa/addon.json`](alexa/addon.json)) | Exposes 9 deterministic tools (`audit_and_score`, `audit_code`, `audit_repository`, `calculate_sci`, `measure_energy`, `get_grid_intensity`, `compare_regions`, `explain_score`, `refactor_code`) over Streamable HTTP (`2025-11-25`+) with RFC 9728 Protected Resource Metadata and OAuth 2.1 PKCE (`S256`). | Lets developers, SREs, and AI agents (Alexa+, Claude Desktop, Cursor, Kiro) run sub-500ms voice or chat queries during code review and job scheduling — for example, checking which AWS region currently has the cleanest grid before launching a batch workload, or asking whether a score was measured by hardware counters. |
| **Amazon Bedrock Converse API** ([`app/bedrock_client.py`](app/bedrock_client.py), [`app/llm_refactor.py`](app/llm_refactor.py)) | Calls `bedrock-runtime` (`converse` API with `Claude 3.5 Haiku` / `Claude 3.5 Sonnet`) only on AST-flagged code snippets (`~300–500` tokens) and validates every candidate rewrite through a 4-stage execution equivalence gate. | Rewrites complex algorithmic bottlenecks into lower-energy equivalents at `< $0.005` per Pull Request while guaranteeing that the refactored function produces identical outputs across 12 test probe inputs. |
| **AWS Custom Silicon Profiler** ([`app/ml_carbon.py`](app/ml_carbon.py), [`app/calibrated_energy.py`](app/calibrated_energy.py), [`app/cloud_cost_mapper.py`](app/cloud_cost_mapper.py)) | Models compute wattage, PUE overhead, Scope 2 $\text{kg CO}_2\text{e}$, and hourly EC2 pricing across x86/GPU instances versus **AWS Graviton4 (`c8g`, `r8g`)**, **AWS Inferentia2 (`inf2` via AWS Neuron SDK)**, and **AWS Trainium1 (`trn1`)**. | Gives engineering teams concrete pre-migration numbers showing how much power (Watt-hours), carbon ($\text{kg CO}_2\text{e}$), and monthly EC2 spend they will save by moving workloads to ARM64 or AWS Neuron accelerators. |
| **AWS Operations CLI** ([`app/aws_cli.py`](app/aws_cli.py)) | Integrates with **AWS SSM Parameter Store**, **Amazon CloudWatch Logs**, **Amazon EventBridge**, **Amazon S3**, and **AWS X-Ray** using `boto3`. | Automates operational tasks: registering MCP endpoints in SSM, tailing audit logs from CloudWatch, scheduling recurring repository audits in EventBridge, archiving signed audit reports in S3, and emitting latency traces to X-Ray. |
| **Multi-Language AST & Tree-sitter Engine** ([`app/parser.py`](app/parser.py)) | Scans 13+ languages (Python `ast`, JavaScript, TypeScript, Go, Rust, Java, C, C++, C#, Ruby, PHP, Bash, SQL) plus lexical fallback to detect 15 Green Software Foundation (GSF) anti-patterns and custom `.greencode-rules.yaml` rules. | Runs locally on CPU in milliseconds with `$0.00` LLM token cost, catching inefficient loops, unbuffered I/O, redundant allocations, and ML anti-patterns on every commit or IDE save. |
| **Hardware Energy Sensors & Function Tracer** ([`app/energy_sensors.py`](app/energy_sensors.py), [`app/energy_tracer.py`](app/energy_tracer.py)) | Reads physical power counters on Linux (`Intel/AMD RAPL`, `Scaphandre`, `perf stat`, battery discharge) with 32-bit counter wrap-around handling and attributes Joules per function via `sys.settrace`. | Identifies the exact function consuming CPU/DRAM Joules during execution and prevents theoretical TDP estimates from ever being misreported as physical hardware measurements. |
| **Pre-Deployment CI/CD Gate & Kubernetes Sentinel** ([`action.yml`](action.yml), [`app/energy_predictor.py`](app/energy_predictor.py), [`app/kubernetes_profiler.py`](app/kubernetes_profiler.py)) | Enforces Green Score thresholds in GitHub Actions and GitLab CI Merge Requests, predicts energy impact before deployment, and monitors live Kubernetes pod power via Kepler/Scaphandre metrics. | Blocks energy-regressing Pull Requests before merge and automatically triggers `kubectl rollout undo` if a deployed microservice spikes `> 35%` above its baseline wattage. |
| **Reality Verification Pipeline & SCI Ledger** ([`app/pipeline/`](app/pipeline/), [`app/sci.py`](app/sci.py)) | Compares predicted savings (`CLAIM`) against HMAC-SHA256 signed hardware counter readings (`EVIDENCE`), records verdicts in a hash-chained ledger, and computes ISO/IEC 21031 (GSF SCI v1.0) scores. | Produces tamper-evident verification records (`VERIFIED` vs. `CONTRADICTED`) and exportable Scope 2/3 carbon disclosure reports for engineering audits and regulatory compliance. |

---

## Cloud Cost, Carbon Reduction, and Inference Economics

GreenCode connects code-level energy analysis to cloud compute cost and carbon accounting:

1. **Pre-Deployment Code, IaC & Pull Request Gatekeeping:**
   - Catches algorithmic energy bottlenecks ($\mathcal{O}(N^3)$ nested loops, N+1 queries, unbuffered I/O, missing `torch.no_grad()`, synchronous GPU-to-CPU transfers, unquantized `FP32` inference) and unoptimized Terraform/Kubernetes resources before inefficient code reaches production.
2. **AWS Custom Silicon Migration Advisor (`Graviton4`, `Inferentia2`, `Trainium1`):**
   - [`app/ml_carbon.py`](app/ml_carbon.py), [`app/calibrated_energy.py`](app/calibrated_energy.py), and [`app/cloud_cost_mapper.py`](app/cloud_cost_mapper.py) model workload energy and cost across **AWS Graviton4 (`c8g.2xlarge`, `r8g.2xlarge`)**, **AWS Inferentia2 (`inf2.xlarge` via AWS Neuron SDK — up to 50% better performance per watt)**, and **AWS Trainium1 (`trn1.2xlarge`)**, quantifying both Scope 2 $\text{kg CO}_2\text{e}$ reductions and EC2 dollar savings.
3. **Regional Carbon & Spot Arbitrage Across 11 AWS Regions:**
   - Compares carbon intensity and compute rates across `eu-north-1` (Stockholm), `ca-central-1` (Montreal), `eu-west-1` (Ireland), `us-west-2` (Oregon), `eu-west-2` (London), `us-east-1` (N. Virginia), `eu-central-1` (Frankfurt), `us-east-2` (Ohio), `ap-northeast-1` (Tokyo), `ap-southeast-1` (Singapore), and `ap-south-1` (Mumbai).
4. **Two-Stage Analysis & Verification Pipeline:**
   - **Stage 1 (Zero-Token Local AST Analysis):** Static code audits, IaC linting, SCI calculations, hardware energy counter reads, and regional grid comparisons run deterministically on CPU with **$0.00 LLM token cost**.
   - **Stage 2 (Targeted Amazon Bedrock Refactoring):** Only flagged function snippets (~300–500 tokens) are sent to **Amazon Bedrock (`Claude 3.5 Haiku` / `Claude 3.5 Sonnet`)** via the Converse API, keeping LLM inference costs under **$0.005 per Pull Request** (**< $2–$6 per 1,000 refactorings**).
   - **Stage 3 (Behaviour-Preserving Verification Gate):** Every LLM-proposed rewrite must pass `compile()`, AST similarity checks, and 12-input execution equivalence testing ([`app/llm_refactor.py`](app/llm_refactor.py)) before acceptance.

> ### Measurement provenance
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

## Repository Structure

```
greencode/
├── app/
│   ├── __init__.py           # Public package exports (GreenCodeSDK, track_energy, v2.0.0)
│   ├── py.typed              # PEP 561 marker for static type checkers (mypy, pyright)
│   ├── sdk.py                # Official Python SDK (GreenCodeSDK) & @track_energy profiler
│   ├── plugins.py            # Extensible PluginRegistry & HMAC-SHA256 webhook dispatcher
│   ├── main.py               # FastAPI backend server & unified CLI (--path, --diff, --iac, --focus-csv)
│   ├── parser.py             # Multi-language AST/Tree-sitter static analysis engine
│   ├── custom_rules.py       # Declarative YAML/JSON custom rule engine (.greencode-rules.yaml)
│   ├── iac_linter.py         # Terraform (.tf), Kubernetes (.yaml), and Dockerfile FinOps/carbon linter
│   ├── finops_focus.py       # FinOps Foundation FOCUS 1.4 cloud billing & carbon reconciler
│   ├── sarif.py              # OASIS SARIF v2.1.0 (with fixes[]) & SonarQube Generic Issue exporter
│   ├── gitlab_client.py      # GitLab API v4 Merge Request Carbon Gate & suggestion:-0+0 bot
│   ├── energy_sensors.py     # Hardware energy counters (RAPL / Scaphandre / perf / battery) + TDP model
│   ├── energy_tracer.py      # Per-function energy attribution via sys.settrace
│   ├── sci.py                # ISO/IEC 21031 (GSF SCI v1.0) & GSF Impact Framework (.imp.yaml) exporter
│   ├── dynamic_analysis.py   # Sandboxed repository execution under measurement (Docker)
│   ├── bedrock_client.py     # Amazon Bedrock Converse API client
│   ├── huggingface_client.py # HuggingFace Inference API client (classified errors)
│   ├── llm_refactor.py       # LLM refactoring + 4-stage behaviour-preserving verification gate
│   ├── mcp_server.py         # Alexa+ self-hosted MCP server (Streamable HTTP, RFC 9728 / PKCE S256)
│   ├── aws_cli.py            # AWS operations CLI (SSM, CloudWatch, EventBridge, S3, X-Ray)
│   ├── ml_carbon.py          # AI/ML carbon & AWS Graviton4 / Inferentia2 / Trainium1 advisor
│   ├── audit_intel.py        # Deterministic root-cause grouping & remediation planning
│   ├── optimizer.py          # Grid carbon intensity client + rule-based refactor engine
│   ├── database.py           # SQLAlchemy historic ledger & metrics persistence
│   ├── audit/                # Modular FastAPI routers for code audit, SARIF, SonarQube, and plugins
│   ├── kubernetes/           # Modular FastAPI routers for K8s pod sentinel and IaC linting
│   ├── routers/              # Modular FastAPI routers (policies, budgets, billing, reports, pr_gate)
│   └── pipeline/             # Reality Verification Pipeline (claim vs. real hardware)
│       ├── config.py         # Environment-driven policy, channels, prod safety checks
│       ├── signing.py        # HMAC authentication + replay rejection for evidence
│       ├── verifier.py       # Claim/evidence comparison -> VERIFIED..CONTRADICTED
│       ├── ledger.py         # Hash-chained, tamper-evident decision records
│       ├── notifier.py       # Slack / Teams / email delivery of verdicts
│       ├── engine.py         # Orchestrator: idempotent intake, verify, record
│       ├── n8n.py            # Generator for the importable n8n workflow
│       └── n8n_workflow.json
├── frontend/                 # React 18 + TypeScript + Vite web console
├── deploy/
│   ├── helm/greencode/       # Kubernetes Helm chart
│   └── gitlab-ci-greencode.yml # GitLab CI/CD Merge Request Carbon Gate template
├── samples/
│   ├── heavy_pipeline.py     # Benchmark script exhibiting 4 GSF anti-patterns
│   └── eco_pipeline.py       # Refactored script free of GSF anti-patterns
├── scripts/
│   ├── measure_and_file_evidence.py # Measure real energy -> file evidence -> get a verdict
│   └── demo_pipeline.py      # Live end-to-end demo of the verification pipeline
├── tests/                    # 515+ automated unit, integration, compliance, and SDK tests
├── .greencode-rules.yaml     # Declarative organization custom energy & FinOps rules
├── .pre-commit-hooks.yaml    # Official pre-commit hook definitions (greencode-audit, greencode-iac)
├── action.yml                # GitHub Action manifest for CI/CD Pull Request gating
├── pyproject.toml            # PEP 621 package metadata, CLI entrypoints, and modular extras
└── requirements.txt          # Pinned dependency specifications
```

---

## Self-Hosted Platform Deployment

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
python -m pytest tests/          # 515+ tests
ENV=development python -m app.main --path . --threshold 75
```

---

## Energy Measurement Tiers

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

## Green Software Foundation (GSF) Patterns Enforced

1. **Deep Nested Iteration (`NESTED_LOOPS_DEPTH_3+`)**:
   - **Severity**: `HIGH` | **Deduction**: `-15 pts`
   - **Physics & Impact**: Loops with depth $\ge 3$ scale computational complexity to $\mathcal{O}(N^3)$, causing runaway CPU instruction cycles and elevated thermal design power (TDP) dissipation.
   - **Remediation**: Flatten iterations using `itertools.product`, generator pipelines, or hash set/dict lookups.

2. **Unmanaged Database Cursors (`RAW_DB_CURSOR_NO_CONTEXT`)**:
   - **Severity**: `HIGH` | **Deduction**: `-10 pts`
   - **Physics & Impact**: Creating DB cursors without a `with` context manager risks persistent unclosed sockets, forcing database servers to sustain unnecessary idle power states.
   - **Remediation**: Enclose cursor operations within `with connection.cursor() as cursor:`.

3. **Un-cached Network Requests Inside Loops (`UNCACHED_NETWORK_IN_LOOP`)**:
   - **Severity**: `CRITICAL` | **Deduction**: `-20 pts`
   - **Physics & Impact**: Synchronous HTTP calls inside iterations trigger repeated Radio / NIC transceiver wake-up energy and redundant TLS connection handshakes.
   - **Remediation**: Batch requests into single bulk endpoints, hoist connections with `requests.Session()`, or apply `@lru_cache` memoization.

4. **Quadratic String Concatenation (`QUADRATIC_STRING_CONCAT_IN_LOOP`)**:
   - **Severity**: `MEDIUM` | **Deduction**: `-8 pts`
   - **Physics & Impact**: Using `+` or `+=` string concatenation inside loops causes quadratic $\mathcal{O}(N^2)$ memory allocations and aggressive garbage collection thrashing.
   - **Remediation**: Accumulate string elements into a list and invoke `''.join(chunks)`.

---

## Multi-Language Static Analysis Engine (AST / Tree-sitter + Lexical Fallback)

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
3. **Declarative Custom Rule Evaluation (`.greencode-rules.yaml`)**:
   Evaluates organization-defined rules from [`.greencode-rules.yaml`](.greencode-rules.yaml) alongside built-in AST rules.
4. **Embedded Code Block Extraction**:
   Extracts and scans embedded code blocks (such as `<script>` tags in HTML and fenced code blocks in Markdown).

---

## Software Carbon Intensity (SCI) Mathematical Model

Operational carbon footprints are calculated in accordance with the Green Software Foundation SCI Standard (ISO/IEC 21031:2024):

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

## Refactoring: Deterministic Rules + Amazon Bedrock Verification Gate

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

## Dynamic Analysis

Static analysis says a pattern *can* be expensive. Dynamic analysis measures
what the program *did* cost. Both are shipped, and they are reported as
distinct things.

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

---

## Badges, Equivalencies, and Disclosure Reports

1. **SVG GitHub README Badges**:
   - Generates SVG badges in Shields.io format at `/api/badge/score/{score}` and `/api/badge/repo/{repo_id}`.
   - Markdown and HTML snippets are provided in the dashboard to display repository Green Scores on GitHub.

2. **EPA Equivalency Calculator**:
   - Translates Joules (and derived Watt-hours, $J / 3600$) into everyday equivalencies using United States Environmental Protection Agency (EPA) factors:
     - **Urban Trees Preserved**: $21.77\text{ kg CO}_2\text{/tree/year}$
     - **Smartphones Charged**: $8.22\text{ Wh/charge}$
     - **Cloud Compute Savings**: AWS EC2 (`Graviton4`, `Inferentia2`, `Trainium1`) compute and cooling billing reduction.
   - Includes a simulation slider scaling from 1,000 to 1,000,000 monthly runs.

3. **ESG, SCI & GSF Impact Framework Disclosure Export**:
   - Generates HTML, CSV, JSON, and `.imp.yaml` Carbon Audit Disclosure Reports aligned with **Green Software Foundation (GSF) SCI v1.0**, **GSF Impact Framework**, **GHG Protocol Scope 2/3**, and **EU CSRD (ESRS E1) / US SEC** reporting structures.
   - Includes SHA-256 verification checksums, grade stamps, metric breakdowns, and print CSS for PDF export.

---

## Reality Verification Pipeline

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
  -d '{"claim_id":"refactor-1042","repo":"zeenat28-ui/greencode","predicted_reduction_pct":50.0,"baseline_energy_joules":1000.0}'

# File real evidence (unsigned is fine in development; see Security below)
curl -X POST http://localhost:8000/api/pipeline/evidence \
  -H "Content-Type: application/json" \
  -d '{"claim_id":"refactor-1042","energy_joules":500.0,"functional_unit":1.0,"measurement_method":"rapl","source":"ci-runner"}'
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

---

## License, Attribution (`NOTICE`), and Contributions

- **Original Author & Copyright Holder:** Copyright (c) 2026 **Zeenat ([@zeenat28-ui](https://github.com/zeenat28-ui))**.
- **License:** Distributed under the [Apache License 2.0](LICENSE) with mandatory attribution enforced via [`NOTICE`](NOTICE) (Section 4(c) & 4(d)).
- **Attribution Requirement:** Any fork, redistribution, or derivative work must preserve both [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE) attributing `@zeenat28-ui`. Removing copyright notices or claiming original authorship terminates license rights under Apache License 2.0.
- **Contributing:** See [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). All Pull Requests require automated CI passage and Code Owner (`@zeenat28-ui`) approval.

## Commercial Plans, License Activation, and Sponsorship

GreenCode follows an open-core model: the static analyzer, Python SDK, CLI, pre-commit hooks, and MCP server are Apache-2.0 licensed, while teams and organizations can unlock higher quotas, automated PR/MR patching, and signed regulatory evidence bundles via a `GC-LIC-...` license key.

| Feature / Quota | Community (`$0 / mo`) | Pro Team (`$49 / mo`) | Organization (`$499 / mo`) |
|---|---|---|---|
| **Monthly Repository Audits** | 50 / month | 1,000 / month | Unlimited |
| **AI Code Refactorings (Bedrock / HF)** | 10 / month | 250 / month | 5,000 / month |
| **Monitored Repositories** | Up to 3 | Up to 25 | Unlimited |
| **13-Language AST, IaC Linter & `--diff` Gate** | Included | Included | Included |
| **GitHub PR & GitLab MR `suggestion` Bot** | Manual CLI | Automated Webhook & PR/MR Bot | Automated + Custom `.greencode-rules.yaml` |
| **Kubernetes Kepler / Pod Wattage Sentinel** | Basic | Full + Auto-Rollback | Multi-Cluster + Prometheus |
| **FinOps FOCUS 1.4 & GSF `.imp.yaml` Export** | Included | Included | Included + Automated Reconciliation |
| **CSRD / SEC Signed Evidence Bundle (`.zip`)** | — | — | Included (`HMAC-SHA256` + Merkle Root) |
| **SAML 2.0 SSO, SCIM 2.0 & S3 WORM Ledger** | — | — | Included |

### How to Purchase and Activate a Commercial License (`GC-LIC-...`)

1. **Subscribe or Back a Commercial Tier:**
   - **Open Collective (Instant Fiscal Host Invoice):** [`opencollective.com/greencode`](https://opencollective.com/greencode) (`>= $49` provisions **Pro**; `>= $499` provisions **Organization** automatically via `POST /api/billing/webhooks/opencollective`).
   - **GitHub Sponsors:** [`github.com/sponsors/zeenat28-ui`](https://github.com/sponsors/zeenat28-ui) (configured in [`.github/FUNDING.yml`](.github/FUNDING.yml)).
2. **Activate in Dashboard, API, or CI/CD:**
   - **Web UI:** Open **Settings &rarr; Plan Quota &amp; License Activation**, paste your `GC-LIC-...` key, and click **Activate License**.
   - **REST API:** `POST /api/billing/license/activate` with `{"license_key": "GC-LIC-..."}`.
   - **GitHub Action (`action.yml`):** Pass `license_key: ${{ secrets.GREENCODE_LICENSE_KEY }}` and `diff_range: origin/main...HEAD`.

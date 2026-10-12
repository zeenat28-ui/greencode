# GreenCode Auditor

[![Release](https://img.shields.io/badge/release-v2.1.0-0ea5e9)](pyproject.toml)
[![CI Gatekeeper](https://img.shields.io/badge/CI%2FCD-Quality%20Gate-success)](action.yml)
[![SCI Standard](https://img.shields.io/badge/ISO%2FIEC%2021031-GSF%20SCI-brightgreen)](https://greensoftware.foundation)
[![FinOps Standard](https://img.shields.io/badge/FinOps-FOCUS%201.4-2563eb)](app/finops_focus.py)
[![OpenTelemetry](https://img.shields.io/badge/CNCF-OTLP%2FHTTP%20v1-f5a800)](app/otel_exporter.py)
[![SARIF](https://img.shields.io/badge/OASIS-SARIF%20v2.1.0-7c3aed)](app/sarif.py)
[![Tests](https://img.shields.io/badge/tests-530%2B%20passing-success)](tests/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Sponsor](https://img.shields.io/badge/Sponsor-Open%20Collective-ea4aaa?logo=opencollective)](https://opencollective.com/greencode-oss)

**GreenCode Auditor** is a static source-code and Infrastructure-as-Code (IaC) energy analyzer, hardware power profiler, FinOps `FOCUS 1.4` cloud billing reconciler, and ISO/IEC 21031 (Green Software Foundation SCI) CI/CD quality gate with native **Amazon Alexa+ (MCP & ASK)**, **Amazon Bedrock**, and **OpenTelemetry (`OTLP/HTTP v1`)** integration.

---

## Core Capabilities

- **Polyglot Static & Cross-File Call-Graph Analysis ([`app/parser.py`](app/parser.py), [`app/call_graph.py`](app/call_graph.py)):** Detects algorithmic energy bottlenecks ($\mathcal{O}(N^3)$ loops, uncached network/DB I/O in loops, unquantized ML inference) across 13+ languages, including cross-module transitive loop I/O across Python, TypeScript/JavaScript, Go, and Rust.
- **Hardware Energy & Process Attribution ([`app/energy_sensors.py`](app/energy_sensors.py), [`app/calibration.py`](app/calibration.py)):** Reads physical power counters (`Intel/AMD RAPL`, `Scaphandre`, `perf`, battery) with Linux `cgroup v2` (`cpu.stat`) and per-PID CPU time-share isolation, backed by SPECpower non-linear utilization curves (`Xeon`, `EPYC`, `AWS Graviton4`, `Apple Silicon`, `NVIDIA NVML`) with 95% confidence intervals.
- **ISO/IEC 21031 SCI & FinOps `FOCUS 1.4` Reconciler ([`app/sci.py`](app/sci.py), [`app/finops_focus.py`](app/finops_focus.py), [`app/iac_linter.py`](app/iac_linter.py)):** Computes Software Carbon Intensity scores with live grid provenance (`UK ESO`, `ENTSO-E`, `Electricity Maps`, `WattTime`), lints Terraform/Kubernetes/Dockerfiles, and reconciles cloud billing exports with Scope 2/3 emissions.
- **OpenTelemetry (`OTLP/HTTP v1`) & SARIF v2.1.0 Exporters ([`app/otel_exporter.py`](app/otel_exporter.py), [`app/sarif.py`](app/sarif.py)):** Exports carbon and SCI gauges (`greencode.sci.gco2e_per_unit`, `greencode.energy.joules`) to Grafana, Datadog, and Prometheus collectors, and emits OASIS SARIF v2.1.0 patches (`fixes[]`) for GitHub Code Scanning and SonarQube.
- **Verified Refactoring via Amazon Bedrock ([`app/bedrock_client.py`](app/bedrock_client.py), [`app/llm_refactor.py`](app/llm_refactor.py)):** Uses the Amazon Bedrock Converse API with a 4-stage verification gate (`compile()`, AST similarity, and 12-input execution equivalence) plus deterministic AST fallback.
- **Amazon Alexa+ & MCP Server ([`app/mcp_server.py`](app/mcp_server.py), [`alexa/`](alexa/)):** Self-hosted Model Context Protocol (`2025-11-25`+) Streamable HTTP server with RFC 9728 / OAuth 2.1 PKCE (`S256`) and native Amazon Alexa Skills Kit (ASK v1.0) webhook (`/alexa/skill`).

---

## Quickstart

### 1. Install

```bash
pip install -e .

# Optional enterprise extras (AWS Bedrock/boto3, Alexa+ MCP server, Tree-sitter, Celery/Redis)
pip install -e ".[aws,mcp,treesitter,distributed]"
```

### 2. Command-Line Interface (`greencode`)

```bash
# Audit a repository and enforce a minimum Green Score gate
greencode --path . --threshold 80.0

# Audit only lines changed in a Pull Request
greencode --path . --diff origin/main...HEAD --threshold 80.0

# Lint Infrastructure-as-Code (.tf, Kubernetes .yaml, Dockerfile)
greencode --iac main.tf

# Reconcile a FinOps Foundation FOCUS 1.4 cloud billing CSV with Scope 2/3 carbon
greencode --focus-csv billing_focus_1_4.csv
```

### 3. Python SDK (`GreenCodeSDK` & `@track_energy`)

```python
from app import GreenCodeSDK, track_energy

sdk = GreenCodeSDK(default_zone="EU-SE")

# 1. Static source code, cross-file call-graph, and IaC auditing
audit = sdk.audit_code("def compute(xs):\n    return [x * 2 for x in xs]\n", language="python")
cg = sdk.audit_call_graph({"api.py": "def run(items):\n    for x in items:\n        fetch(x)\n", "db.py": "def fetch(x):\n    requests.get(x)\n"})

# 2. Measure runtime energy (Joules) and SCI (gCO2e / unit)
with track_energy("batch_etl_job", zone="IE", functional_unit=100.0) as meter:
    total = sum(i * i for i in range(250_000))

# 3. Export OpenTelemetry (OTLP/HTTP v1 JSON) metrics
otlp = sdk.export_otlp(service_name="billing-worker", green_score=audit["green_score"], energy_joules=meter.result["energy_joules"])
```

### 4. GitHub Actions (`action.yml`) & Pre-Commit

```yaml
# .github/workflows/greencode.yml
- name: Run GreenCode Quality Gate
  uses: zeenat28-ui/greencode@main
  with:
    repo-path: "."
    green-score-threshold: "80.0"
    target-zone: "US-CAL-CISO"
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/zeenat28-ui/greencode
    rev: v2.1.0
    hooks:
      - id: greencode-audit
      - id: greencode-iac
```

---

## Amazon Alexa+ (MCP & Custom Skill) and AWS CLI

Start the MCP (`2025-11-25`+) and Alexa Custom Skill server locally:

```bash
python -m app.mcp_server
# MCP Streamable HTTP: http://127.0.0.1:8765/mcp
# Alexa ASK Webhook:   http://127.0.0.1:8765/alexa/skill

# Run live end-to-end compliance checks:
python check_mcp_alexa.py
```

AWS Operations CLI ([`app/aws_cli.py`](app/aws_cli.py)):

```bash
python -m app.aws_cli mcp register        # Register MCP URI in AWS SSM Parameter Store
python -m app.aws_cli logs tail           # Tail audit logs from Amazon CloudWatch Logs
python -m app.aws_cli schedule enable     # Configure nightly audit in Amazon EventBridge
python -m app.aws_cli s3 push report.json # Archive signed audit evidence to Amazon S3
```

---

## Self-Hosted Deployment & Testing

```bash
# 1. Configure environment secrets and launch Docker stack (React UI :3000, FastAPI :8000)
cp .env.example .env
docker compose up -d --build

# 2. Run the automated test suite locally
python -m pytest tests/ -q
```

> **Measurement Provenance Note:** Every energy figure carries `measurement_method` (`rapl`, `scaphandre`, `perf`, `battery`, or `model`) and `measurement_is_hardware` (`true`/`false`). Hardware counters require a native Linux host exposing `/sys/class/powercap`; on Windows/WSL2 or unprivileged VMs, estimates are transparently tagged as `model` (`measurement_is_hardware=false`) with SPECpower calibration intervals.

---

## Documentation

| Document | Description |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture, AST/Tree-sitter engine, SCI math, and Reality Verification Pipeline |
| [`docs/API.md`](docs/API.md) | REST API endpoints (`/api/audit`, `/api/audit/call-graph`, `/api/audit/telemetry/otlp`, `/api/billing/focus-reconcile`) |
| [`docs/MEASUREMENT_PLATFORMS.md`](docs/MEASUREMENT_PLATFORMS.md) | Hardware energy tiers (`RAPL`, `cgroup v2`, `Scaphandre`, `perf`) and grid intensity providers |
| [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) | ISO/IEC 21031 (GSF SCI), GHG Protocol Scope 2/3, EU CSRD (ESRS E1), and FinOps FOCUS 1.4 |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Production Docker Compose, Kubernetes Helm chart (`deploy/helm/greencode`), and security hardening |
| [`alexa/README.md`](alexa/README.md) | Amazon Alexa+ MCP Server & ASK Custom Skill setup and interaction model |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`SECURITY.md`](SECURITY.md) | Contribution guidelines, code standards, and vulnerability disclosure policy |

---

## License

Licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE) for details.

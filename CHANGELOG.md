# Changelog

All notable changes, security fixes, and architectural releases for **GreenCode** are documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2.0.0] - 2026-10-12

### Added
- **Live 3-Tier Runtime Energy Profiler (`app/kubernetes_profiler.py`, `app/routers/energy_deployment.py`):**
  - Added `GET /api/energy/workloads` with automatic telemetry cascade: CNCF Kepler Prometheus (`/metrics`) -> Docker Engine container stats -> host `psutil` process power telemetry.
  - Added `POST /api/energy/workloads/baseline`, `POST /api/energy/budgets/allocate`, and `POST /api/energy/budgets/evaluate-pr` for team carbon budget enforcement.
- **Local Workspace & Git Diff Static Analyzer (`app/main.py`, `action.yml`):**
  - Added `POST /api/scan/local-workspace` with workspace-root path confinement (`os.path.realpath`) and automatic SQLite/PostgreSQL persistence.
  - Added `--diff <base>...<head>` CLI flag (`python -m app.main --path . --diff origin/main...HEAD --ci`) and `diff_range` input in `action.yml` for incremental Pull Request hunk gating.
- **Multi-Language Loop Hazard Rules & Unified Patch Synthesis (`app/parser.py`, `app/optimizer.py`):**
  - Added `ViolationType.HEAVY_CLIENT_INSTANTIATION_IN_LOOP` detecting SDK/HTTP client instantiation (`boto3.client`, `httpx.Client`, `OpenAI`, `Anthropic`, `new S3Client`, `new HttpClient`) inside loops across Python, JS/TS, Go, Rust, Java, and C#.
  - Added non-Python loop hazard checks for `JSON.parse`/`JSON.stringify`, regex compilation (`new RegExp`, `Pattern.compile`, `regexp.MustCompile`), and synchronous file I/O (`fs.readFileSync`, `fs.writeFileSync`).
  - Added `generate_unified_diff()` and `generate_github_suggestion_block()` to `app/optimizer.py` and wired collapsible patch suggestions into GitHub PR comments (`app/github_client.py`).
- **Cryptographic Commercial Licensing & Open Collective Webhook (`app/pricing.py`, `app/routers/billing.py`):**
  - Added `LicenseKeyManager` for HMAC-SHA256 signed `GC-LIC-<payload>.<sig>` license issuance and constant-time verification (`hmac.compare_digest`).
  - Added `POST /api/billing/license/issue`, `POST /api/billing/license/activate`, and `POST /api/billing/webhooks/opencollective` for automated Pro/Organization tier provisioning.
- **CSRD / SEC Cryptographic Evidence Bundle (`app/routers/reports.py`, `app/reports/esg_report.py`):**
  - Added `GET /api/reports/esg/{org_id}/evidence-bundle` and `GET /api/reports/esg/{org_id}/evidence-manifest` generating signed `.zip` archives with `X-Bundle-Root-SHA256` verification headers.

### Changed
- **Zero Synthetic Fallback Data (`frontend/src/`, `app/routers/`):**
  - Connected `EnergyControlPlane.tsx`, `Reports.tsx`, `Settings.tsx`, `ScanRepository.tsx`, `Dashboard.tsx`, `GitHubBotPreviewModal.tsx`, `FinOpsCalculatorModal.tsx`, and `AlexaVoiceCockpit.tsx` directly to live FastAPI endpoints.

### Security
- **Zero Open Dependabot Alerts (`requirements.txt`, `frontend/package.json`, `.github/workflows/`):**
  - Upgraded `pyjwt` to `2.15.0`, `cryptography` to `50.0.2`, `uvicorn` to `0.54.0`, `streamlit` to `1.65.0`, `asyncpg` to `0.32.0`, `tree-sitter` to `0.26.0`, `vite` to `8.3.4`, `react-router-dom` to `7.18.4`, and `postcss-selector-parser` to `7.1.6`.
  - Upgraded GitHub Actions (`actions/checkout`, `actions/setup-python`, `actions/setup-node`, `actions/upload-artifact`, `github/codeql-action`, `gitleaks/gitleaks-action`) to latest major versions.

---

## [1.2.0] - 2026-10-09

### Added
- **Alexa+ Voice MCP Agent (`app/mcp_server.py`, `alexa/addon.json`):**
  - Implemented self-hosted MCP server over Streamable HTTP (`2025-11-25`+) with RFC 9728 Protected Resource Metadata (`/.well-known/oauth-protected-resource`) and OAuth 2.1 PKCE (`S256`).
  - Exposed 9 deterministic MCP tools (`audit_and_score`, `audit_code`, `audit_repository`, `calculate_sci`, `measure_energy`, `get_grid_intensity`, `compare_regions`, `explain_score`, `refactor_code`).
- **Amazon Bedrock Converse API & 4-Stage Verification Gate (`app/bedrock_client.py`, `app/llm_refactor.py`):**
  - Integrated `bedrock-runtime` Converse API (`Claude 3.5 Haiku` / `Claude 3.5 Sonnet`) with AST token similarity and 12-input execution equivalence testing.
- **Reality Verification Pipeline (`app/pipeline/`):**
  - Added HMAC-SHA256 signed hardware evidence intake (`POST /api/pipeline/evidence`) and hash-chained tamper-evident ledger (`app/pipeline/ledger.py`).

---

## [1.0.0] - 2026-09-25

### Added
- Initial release of GreenCode AST Static Analyzer, Green Software Foundation SCI v1.0 calculator (`app/sci.py`), Linux RAPL/Scaphandre/perf hardware energy sensors (`app/energy_sensors.py`), and FastAPI + React dashboard.

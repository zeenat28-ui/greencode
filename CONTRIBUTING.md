# Contributing to GreenCode Auditor

Thank you for contributing to **GreenCode Auditor** — an open-source Software Carbon Intensity (GSF SCI v1.0 / ISO/IEC 21031) static analyzer, hardware/cloud power telemetry profiler, Amazon Bedrock refactoring engine, and Alexa+ MCP server.

---

## Development Environment Setup

### 1. Prerequisites
- **Python:** 3.11 or 3.12
- **Node.js:** 20+ (for the React + Vite + Tailwind web UI in `frontend/`)
- **Docker:** Optional (required only when running container-sandboxed dynamic profiling via `/api/dynamic/analyze`)

### 2. Backend Setup
```bash
git clone https://github.com/zeenat28-ui/greencode.git
cd greencode
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-cov pre-commit
```

### 3. Frontend Setup
```bash
cd frontend
npm ci
npm run build
```

### 4. Secret Hygiene & Pre-Commit Hooks
Never commit API keys, `.env` files, or cloud credentials. Install the pre-commit hooks before creating commits:
```bash
pre-commit install
```

---

## Running the Test Suite

Every pull request must pass the automated test suite and static checks:

```bash
# Run the full pytest suite
python -m pytest tests/ -q

# Verify Python bytecode compilation
python -m compileall -q app tests

# Verify frontend TypeScript & Vite production build
cd frontend && npm run build
```

---

## Engineering Standards

1. **No Fabricated Telemetry or Placeholder Data:**
   - Every energy figure (`energy_joules`), carbon intensity value (`gCO2eq/kWh`), and cloud cost calculation must carry provenance metadata (`source`, `method`, `tier`, `citation`, and `measurement_is_hardware`).
   - When hardware counters (Linux RAPL / `/sys/class/powercap`) or live grid APIs are unreachable, code must either fail closed or explicitly label output as `model` / `static_matrix` with cited reference sources (Ember 2024, EPA eGRID, SPECpower, GSF SCI v1.0).
2. **AST Verification for Refactorings:**
   - Any refactoring rule in `app/parser.py`, `app/optimizer.py`, or `app/llm_refactor.py` must pass syntax and behavioral equivalence verification before being returned to callers.
3. **Multi-Tenant Isolation & Audit Logging:**
   - API endpoints under `app/routers/` must enforce organization boundaries (`org_id`) and record state-mutating operations in the SHA-256 hash-chained `AuditLogManager`.

---

## Pull Request Workflow

1. Fork the repository and create a feature branch from `main` (`git checkout -b feat/your-feature-name`).
2. Add unit and integration tests under `tests/` covering your changes.
3. Verify that all tests and static checks pass locally.
4. Open a Pull Request using `.github/PULL_REQUEST_TEMPLATE.md`.

---

## Intellectual Property & Contributor License Agreement (CLA)

1. **Original Authorship & Mandatory Attribution (`NOTICE`):**
   - **GreenCode Auditor** is created and maintained by **Zeenat ([@zeenat28-ui](https://github.com/zeenat28-ui))**.
   - Under **Section 4(c) and Section 4(d) of the Apache License 2.0**, any fork, copy, redistribution, or derivative work must preserve the [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE) files intact.
2. **Inbound Contributor License Agreement (CLA):**
   - By submitting a Pull Request or contribution to this repository, you certify under the Developer Certificate of Origin (DCO) that you have the right to submit the work and grant **Zeenat (`@zeenat28-ui`)** a perpetual, worldwide, non-exclusive, royalty-free, irrevocable license under [Apache License 2.0 (Section 5)](LICENSE) to include, maintain, and distribute your contribution as part of GreenCode Auditor.
3. **Protected Main Branch:**
   - Direct pushes to `main` by external users are blocked. All community contributions are submitted via Fork and Pull Request and require Code Owner approval from `@zeenat28-ui`.

---

## Funding and Sponsorship

- **Open Collective:** [`opencollective.com/greencode`](https://opencollective.com/greencode)
- **GitHub Sponsors:** [`github.com/sponsors/zeenat28-ui`](https://github.com/sponsors/zeenat28-ui) (configured via [`.github/FUNDING.yml`](.github/FUNDING.yml)).

# Contributing to GreenCode Auditor

Thank you for your interest in contributing to **GreenCode Auditor** — the open-source enterprise Software Carbon Intensity (GSF SCI v1.0) static analyzer, hardware/cloud telemetry engine, AWS Bedrock eco-refactoring agent, and Alexa+ MCP server.

---

## 🛠️ Development Environment Setup

### 1. Prerequisites
- **Python:** 3.11 or 3.12
- **Node.js:** 20+ (for the React + Vite + Tailwind enterprise dashboard in `frontend/`)
- **Docker:** Optional (required only when running live container-sandboxed dynamic profiling via `/api/dynamic/analyze`)

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
Never commit real API keys, `.env` files, or cloud credentials. Install the repository's pre-commit hooks before creating commits:
```bash
pre-commit install
```

---

## 🧪 Running the Test Suite

Every pull request must pass the full automated test suite and static security checks:

```bash
# Run the full pytest suite
python -m pytest tests/ -q

# Verify Python bytecode compilation
python -m compileall -q app tests

# Verify frontend TypeScript & Vite production build
cd frontend && npm run build
```

---

## 📐 Engineering & Scientific Standards

1. **No Fabricated Telemetry or Placeholder Data:**
   - Every energy figure (`energy_joules`), carbon intensity value (`gCO2eq/kWh`), and cloud cost calculation must carry provenance metadata (`source`, `method`, `tier`, `citation`, and `measurement_is_hardware`).
   - When hardware counters (Linux RAPL / `/sys/class/powercap`) or live grid APIs are unreachable, code must either fail closed or explicitly label output as `model` / `static_matrix` with cited reference sources (Ember 2024, EPA eGRID, SPECpower, GSF SCI v1.0).
2. **AST Verification for Refactorings:**
   - Any new refactoring rule in `app/parser.py`, `app/optimizer.py`, or `app/llm_refactor.py` must pass syntax and behavioral equivalence verification before being returned to callers.
3. **Multi-Tenant Isolation & Audit Logging:**
   - New enterprise endpoints under `app/routers/` must enforce tenant boundaries (`org_id`) and record state-mutating operations in the SHA-256 hash-chained `AuditLogManager`.

---

## 🔄 Pull Request Workflow

1. Fork the repository and create a feature branch from `main` (`git checkout -b feat/your-feature-name`).
2. Add unit and integration tests under `tests/` covering your changes.
3. Ensure all GitHub Actions checks (`GreenCode Quality`, `Secret Scanning`, `Automated Security Audit & Vulnerability Scan`, and `GreenCode Carbon Gatekeeper`) pass.
4. Open a Pull Request filling out `.github/PULL_REQUEST_TEMPLATE.md`.

---

## 📄 License

By contributing to GreenCode Auditor, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

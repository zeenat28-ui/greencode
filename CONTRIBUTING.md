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

## 🛡️ Intellectual Property, Contributor License Agreement (CLA) & Anti-Plagiarism

1. **Original Authorship & Mandatory Attribution (`NOTICE`):**
   - **GreenCode Auditor** is originally created and maintained by **Zeenat ([@zeenat28-ui](https://github.com/zeenat28-ui))**.
   - Under **Section 4(c) and Section 4(d) of the Apache License 2.0**, any fork, copy, redistribution, or derivative work MUST preserve the [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE) files intact. Removing attribution or claiming this codebase as your own original work violates the license and triggers an immediate DMCA Takedown.
2. **Inbound Contributor License Agreement (CLA):**
   - By submitting a Pull Request or contribution to this repository, you certify under the Developer Certificate of Origin (DCO) that you have the right to submit the work and you grant **Zeenat (`@zeenat28-ui`)** a perpetual, worldwide, non-exclusive, royalty-free, irrevocable license under [Apache License 2.0 (Section 5)](LICENSE) to include, maintain, and distribute your contribution as part of GreenCode Auditor.
3. **Protected Main Branch:**
   - Direct pushes to `main` by external users are blocked. All community contributions are submitted via Fork $\rightarrow$ Pull Request and require automated CI/Security gate passage plus explicit Code Owner approval from `@zeenat28-ui`.

---

## 💖 Funding & Sponsorship

If you or your organization would like to fund or sponsor the development of GreenCode Auditor:
- Click the **Sponsor** button at the top of [`zeenat28-ui/greencode`](https://github.com/zeenat28-ui/greencode) (configured via [`.github/FUNDING.yml`](.github/FUNDING.yml)).
- For enterprise grants, custom cloud integrations, or commercial support agreements, reach out via GitHub Discussions or repository issues.



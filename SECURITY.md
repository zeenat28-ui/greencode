# 🔒 GreenCode Security Policy & Controls

## Security Governance & Disclosure
GreenCode Auditor treats security as a foundational requirement. Because our platform executes static parsing, dynamic container sandboxing, and evidence verification for enterprise software systems, we enforce strict zero-trust principles across all code paths.

### Reporting a Vulnerability
If you discover a security vulnerability within GreenCode Auditor, please report it immediately:
- **Email:** `security@greencode.io`
- **PGP Key / Response Window:** Initial response within **24 hours**, triage and patch timeline within **72 hours**.
- **Coordinated Disclosure:** We request that vulnerabilities are not disclosed publicly until a formal remediation patch has been verified and released.

---

## 🛡️ Production Security Architecture

### 1. Zero-Trust Dynamic Sandboxing (RCE Mitigation)
- Dynamic code profiling executes strictly within isolated Docker containers.
- **Rootless execution:** All workloads run as an unprivileged user (`nobody` / non-root).
- **Capability dropping:** `cap_drop: ["ALL"]` and `no-new-privileges` enforced.
- **Read-Only Root Filesystem:** Target repositories are mounted read-only with a transient tmpfs for scratch operations.
- **Network Isolation:** Sandbox containers have external network egress disabled (`network_mode: none`).
- **No Host Fallback:** Untrusted execution on the host OS is blocked fail-closed; if the Docker engine is unreachable, the system reports `sandbox_unavailable` instead of risking host code execution.

### 2. Cryptographic Reality Verification & Tamper-Evident Ledger
- Energy claims and hardware evidence intake are authenticated using **HMAC-SHA256** machine signatures (`X-GreenCode-Signature`).
- Timestamps are validated against strict replay windows to reject duplicate or delayed telemetry.
- Decision records are appended to an immutable, hash-chained cryptographic ledger (`SHA256(seq | prev_hash | canonical_payload)`).
- Any attempt to alter historical audit records breaks the chain from genesis and is flagged via `/api/pipeline/ledger/verify`.

### 3. Credential & Secrets Hygiene
- Secrets are encrypted at rest using **Fernet (AES-128-CBC with HMAC-SHA256)** encryption.
- In production (`ENV=production`), the backend enforces fail-closed startup guards (`test_production_readiness.py`) that refuse to boot if default or insecure keys are detected.
- All published ports bind to `127.0.0.1` (loopback only) by default in `docker-compose.yml`.

---

## 🔍 Automated Continuous Security Pipeline
The codebase is audited continuously across every Pull Request and release:
- **SAST (Static Analysis):** GitHub CodeQL + Bandit Python security scanner.
- **Dependency Auditing:** Snyk + pip-audit + Dependabot alerts.
- **Container Vulnerability Scanning:** Trivy image and SBOM vulnerability scanning.
- **API Security:** OWASP ZAP baseline dynamic application security testing (DAST).


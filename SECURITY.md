# GreenCode Security Policy & Controls

## Security Governance & Vulnerability Reporting
GreenCode Auditor executes static parsing, optional Docker-sandboxed dynamic analysis, and HMAC-authenticated evidence verification.

### Reporting a Vulnerability
If you discover a security vulnerability in this repository, please open a private GitHub Security Advisory on [`zeenat28-ui/greencode`](https://github.com/zeenat28-ui/greencode/security/advisories) so a fix can be verified before public disclosure.

---

## Implemented Security Controls in Code

### 1. Docker-Sandboxed Dynamic Analysis (`app/dynamic_analysis.py`)
- Dynamic code profiling (`POST /api/dynamic/analyze`) executes inside isolated Docker containers.
- **Rootless execution:** Workloads run as an unprivileged user (`65534:65534` / non-root).
- **Capability dropping:** `cap_drop=["ALL"]` and `security_opt=["no-new-privileges"]` enforced.
- **Read-Only Root Filesystem:** Target repositories are mounted read-only with a transient `tmpfs` (`/tmp`) for scratch operations.
- **Network Isolation:** Sandbox containers run with external network egress disabled (`network_mode="none"`).
- **Fail-Closed Without Docker:** Host-level execution of untrusted code is never used as a fallback; if the Docker daemon is unreachable, the endpoint returns `sandbox_unavailable`.

### 2. HMAC Evidence Signing & Hash-Chained Ledger (`app/pipeline/signing.py`, `app/pipeline/ledger.py`, `app/audit_logs.py`)
- Hardware evidence intake (`POST /api/pipeline/evidence`) supports **HMAC-SHA256** verification (`X-GreenCode-Signature`) over `<timestamp>.<raw_body>`.
- Timestamps outside the configured skew window are rejected with classified error codes (`missing_timestamp`, `signature_mismatch`, `stale_timestamp`).
- Pipeline decisions (`app/pipeline/ledger.py`) and organizational audit events (`app/audit_logs.py`) are linked in a SHA-256 hash chain (`prev_hash` $\rightarrow$ `record_hash`) and verified via `/api/pipeline/ledger/verify` and `/api/reports/audit-logs/{org_id}/verify`.

### 3. Credential Encryption & Startup Guards (`app/database.py`, `app/core/config.py`)
- Stored credentials (such as GitHub Personal Access Tokens) are encrypted at rest using **Fernet (AES-128-CBC with HMAC-SHA256)** when `SECRETS_ENCRYPTION_KEY` is configured (`app/database.py`).
- In production mode (`ENV=production`), startup validation refuses insecure default secrets (`tests/test_production_readiness.py`).
- Published ports in `docker-compose.yml` bind to `127.0.0.1` (loopback only) by default.

---

## Security & Compliance Verification Tests
All security controls above are verified by the automated `pytest` suite included in this repository:
```bash
python -m pytest tests/test_dynamic_analysis.py tests/test_pipeline.py tests/test_production_readiness.py tests/test_alexa_compliance.py -q
```

# GreenCode Incident & Regression Response Guide

**Audience:** Self-Hosted Operators & DevSecOps Engineers

## 1. Scope
This guide describes how GreenCode's automated safeguards respond to software energy regressions, ledger tampering, and configuration faults.

---

## 2. Automated Safeguards Implemented in Code
1. **Deployment Power Spike Rollback (`app/kubernetes_profiler.py`, `app/services/rollback_service.py`):**
   - Evaluates observed pod wattage against registered baseline wattage (`POST /api/energy/rollback` or `POST /api/kubernetes/evaluate-rollback`).
   - When $\Delta \text{Power} \ge 35\%$, triggers an automated rollback if `KUBERNETES_SERVICE_HOST` (`execution_mode="k8s_api"`) or `KUBECONFIG` (`execution_mode="kubectl"`) is configured, or logs an auditable dry-run simulation (`is_live_cluster=False, execution_mode="simulated_dry_run"`).
2. **Tamper-Evident Audit Trail (`app/audit_logs.py`, `app/pipeline/ledger.py`):**
   - Every policy update, budget allocation, and rollback evaluation is appended to a SHA-256 hash chain (`prev_hash` $\rightarrow$ `record_hash`).
   - Run `GET /api/reports/audit-logs/{org_id}/verify` or `GET /api/pipeline/ledger/verify` during post-incident reviews to verify that no historical records were altered.
3. **Ephemeral Source Code Parsing (`app/parser.py`):**
   - Source files are parsed in memory to extract AST/CST violation metrics without storing customer source code blobs in the database.

---

## 3. Reporting Security Issues
To report a security vulnerability in the GreenCode codebase, open a private GitHub Security Advisory at [`https://github.com/zeenat28-ui/greencode/security/advisories`](https://github.com/zeenat28-ui/greencode/security/advisories).


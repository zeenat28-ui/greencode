# GreenCode Technical Security & Architecture Reference

> **Scope & Audit Disclaimer:** This document maps GreenCode's implemented application controls to common security and sustainability engineering concepts for technical reviewers. GreenCode is a self-hosted software application and has **not** undergone an independent third-party SOC 2 Type II or ISO 14064-1 audit.

---

## 1. Application Security & Access Control Mappings

| Control Area | Implemented Application Feature | Source Code Location |
| :--- | :--- | :--- |
| **Role-Based Access Control** | Role hierarchy (`superadmin`, `org_admin`, `team_lead`, `developer`, `auditor`, `viewer`) and permission dependencies; SAML/OIDC/SCIM configuration helpers. | [`app/auth/roles.py`](../app/auth/roles.py), [`app/enterprise_governance.py`](../app/enterprise_governance.py), [`app/routers/governance.py`](../app/routers/governance.py) |
| **Tenant Scoping** | Multi-tenant SQLAlchemy schema (`org_id` foreign keys on teams, projects, budgets, invoices, and audit logs) and regional residency policy checks (`EU_STRICT`, `US_STRICT`). | [`app/database.py`](../app/database.py), [`app/services/org_service.py`](../app/services/org_service.py), [`app/enterprise_governance.py`](../app/enterprise_governance.py) |
| **Tamper-Evident Audit Logging** | SHA-256 hash-chained `AuditLog` entries (`prev_hash` $\rightarrow$ `record_hash`) and JSONL pipeline ledger with integrity verification endpoints. | [`app/audit_logs.py`](../app/audit_logs.py), [`app/pipeline/ledger.py`](../app/pipeline/ledger.py) |
| **CI/CD Gate & SARIF Export** | Static AST/CST quality gate with OASIS SARIF v2.1.0 report generation and HMAC-SHA256 signed evidence intake. | [`app/sarif.py`](../app/sarif.py), [`app/pipeline/signing.py`](../app/pipeline/signing.py) |

---

## 2. Data Privacy & Credential Handling
1. **In-Memory Source Code Parsing**: Source files submitted for static analysis (`app/parser.py`) are parsed in memory to extract violation metrics and line numbers; full source code files are not stored in the database.
2. **Data Residency Policy Helper**: `app/enterprise_governance.py` provides configurable residency policy checks (`EU_STRICT`, `US_STRICT`, `GLOBAL`) for routing regional grid queries.
3. **Credential Encryption at Rest**: Stored GitHub tokens in `app/database.py` are encrypted using **Fernet (AES-128-CBC with HMAC-SHA256)** when `SECRETS_ENCRYPTION_KEY` is set.

---

## 3. Dual-Stream Energy Accounting & Provenance (`app/energy_sensors.py`, `app/calibrated_energy.py`)
GreenCode explicitly distinguishes physical hardware counter measurements from model estimates on every API and MCP response:

1. **Hardware Measurement Tier (`measurement_is_hardware: true`)**:
   - Reads bare-metal Linux Intel/AMD RAPL (`/sys/class/powercap`), Scaphandre Prometheus metrics, `perf stat` PMU counters, or battery discharge sensors when available on the host.
2. **Calibrated Model Tier (`measurement_is_hardware: false`, `measurement_method: "model"`)**:
   - On hosts without hardware counter passthrough (Windows, macOS, WSL2, standard cloud VMs), derives estimated energy using SPECpower and Cloud Carbon Footprint (CCF) power curves across AWS Graviton4 (`c8g`), AWS Inferentia2 (`inf2`), AWS Trainium1 (`trn1`), Intel Xeon, and AMD EPYC profiles.

---

## 4. Verification & Test Coverage
All controls described in this document are verified by the automated test suite (`438` tests across `tests/`):
```bash
python -m pytest tests/ -q
```


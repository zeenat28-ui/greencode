# Enterprise Data Retention and Handling Policy

## 1. Scope & Objective
This policy governs the retention, archiving, and deletion of telemetry data, AST scan records, user credentials, and cryptographic audit logs within GreenCode Enterprise.

---

## 2. Retention Schedules

| Data Classification | Description | Retention Period | Archival / Pruning Action |
| :--- | :--- | :--- | :--- |
| **Audit Logs** | Cryptographically chained policy decisions, rollback events, and administrative actions | **7 Years** | WORM-compliant cold storage (immutable) |
| **AST Scan Violations** | Individual file snippets and code deductions | **90 Days** | Purged automatically after 90 days |
| **Energy & Carbon Metrics** | Rollup Joules, SCI, and kWh metrics per deployment | **3 Years** | Retained for SEC/ESG multi-year comparisons |
| **User & GitHub Tokens** | Encrypted OAuth tokens (Fernet AES-256) | **Until revoked** | Immediately scrubbed upon user revocation |

---

## 3. Cryptographic Immutability
All audit records are linked using SHA-256 hash chains (`prev_hash` $\to$ `record_hash`). Even upon archival, the cryptographic chain integrity is preserved and verifiable via `GET /api/reports/audit-logs/{org_id}/verify`.


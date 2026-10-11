# GreenCode Standards Alignment & Audit Trail Reference

See full technical details in [docs/COMPLIANCE.md](docs/COMPLIANCE.md).

> **Scope & Certification Disclaimer:** GreenCode is an open-source software engineering tool that implements the mathematical formulas and cryptographic hash-chaining structures listed below. It has **not** undergone an independent third-party SOC 2 Type II or ISO 14064-1 certification audit.

## Implemented Technical Calculations & Controls
- **Green Software Foundation (GSF) SCI v1.0 (`app/sci.py`)**: Implements $SCI = \frac{(E \times I) + M}{R}$ with explicit hardware vs. model provenance (`measurement_is_hardware`).
- **GHG Protocol Scope 2 & Scope 3 Estimates (`app/reports/esg_report.py`)**: Computes operational electricity emissions ($E \times I$) and amortized embodied server emissions ($M$).
- **Tamper-Evident Audit Trail (`app/audit_logs.py`, `app/pipeline/ledger.py`)**: Appends SHA-256 hash-chained records (`prev_hash` $\rightarrow$ `record_hash`) verifiable via `GET /api/reports/audit-logs/{org_id}/verify` and `GET /api/pipeline/ledger/verify`.
- **SARIF v2.1.0 Output (`app/sarif.py`)**: Exports static analysis violations in OASIS SARIF format for GitHub Code Scanning.


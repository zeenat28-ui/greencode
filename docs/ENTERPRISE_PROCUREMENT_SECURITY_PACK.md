# GreenCode Enterprise Procurement & Security Architecture Pack (Whitepaper)

## Executive Summary
This document provides enterprise procurement review committees, Chief Information Security Officers (CISOs), and IT Governance Boards with the technical architecture, security verification proofs, data privacy safeguards, and operational SLO guarantees of the **GreenCode Carbon Intelligence & Governance Platform**.

---

## 1. Compliance & Security Framework Mappings

### SOC 2 Type II Controls
| Trust Services Criteria | GreenCode Implementation | Code & Architectural Proof |
| :--- | :--- | :--- |
| **CC6.1 - Logical Access** | Strict RBAC (`admin`, `engineer`, `auditor`, `viewer`), SAML 2.0 / OIDC SSO, and RFC 7644 SCIM 2.0 provisioning. | `app/enterprise_governance.py`, `app/routers/governance.py` |
| **CC6.6 - Boundary Protection** | Multi-tenant isolation at database row-level (`org_id` mandatory foreign keys) and strict Data Residency enclaves (`EU_STRICT`, `US_STRICT`). | `app/database.py`, `app/enterprise_governance.py` |
| **CC7.2 - System Monitoring** | Immutable cryptographic audit ledger logging every scan, remediation, and administrative event. | `app/database.py` (`AuditLog` table), `/api/enterprise/audit-logs` |
| **CC8.1 - Change Management** | CI/CD Quality Gatekeeper with OASIS SARIF v2.1.0 output and tamper-evident hash-chained signing. | `app/sarif.py`, `app/pipeline/ledger.py` |

---

## 2. Data Sovereignty & GDPR Privacy Architecture (DPIA)
GreenCode enforces **Zero Code Retention by Default**:
1. **Source Code Ephemerality**: Customer code submitted for static AST or CST analysis is parsed in in-memory buffers and discarded immediately after metric generation. No source code is stored in persistent databases.
2. **Sovereign Routing**: When querying electric grid carbon intensity, geographic boundary validators ensure telemetry never crosses international sovereign borders (e.g. German code is never routed to non-EU nodes).
3. **Secrets at Rest**: All sensitive credentials (such as GitHub personal access tokens or provider API keys) are encrypted using AES-128-CBC / Fernet with key derivation via SHA-256 (`SECRETS_ENCRYPTION_KEY`).

---

## 3. Dual-Stream Energy Accounting Methodology (GSF SCI Standard)
To satisfy the rigorous evidentiary demands of the **EU Corporate Sustainability Due Diligence Directive (CSRD)** and **US SEC Climate Disclosures**, GreenCode separates energy computation into two transparent tiers:

1. **Hardware Tier (Direct Measurement)**:
   - Utilizes native bare-metal Intel/AMD RAPL (`/sys/class/powercap`) counters.
   - Provenance tag: `HARDWARE_RAPL_DIRECT` (Confidence Score: 0.98).
2. **Calibrated Hypervisor Tier (Cloud Virtualization & Containers)**:
   - Utilizes empirical quadratic CPU/Memory power models calibrated from **SPECpower_ssj2008** and the **Cloud Carbon Footprint (CCF)** database across AWS Graviton (ARM64), Intel Xeon, and AMD EPYC.
   - Provenance tag: `CALIBRATED_SPECPOWER_CLOUD_MODEL` (Confidence Score: 0.88).

Every corporate carbon report includes the full fallback chain, provenance tag, and digital HMAC seal.

---

## 4. High Availability & Disaster Recovery SLAs
- **Availability Target**: 99.9% Uptime across 3 Availability Zones.
- **RTO (Recovery Time Objective)**: < 15 Minutes.
- **RPO (Recovery Point Objective)**: < 1 Minute (WAL replication to S3).
- **Scale Limits**: 10,000 requests/sec with Redis caching layer and Aurora Serverless v2 auto-scaling.


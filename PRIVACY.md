# Privacy and Data Processing Policy

**Effective Date:** January 1, 2026  
**Last Updated:** October 2026

## 1. Introduction
GreenCode ("we", "our", or "us") provides software energy analysis, carbon gatekeeping, and CI/CD compliance services for engineering organizations. This Privacy and Data Processing Policy outlines how we collect, process, secure, and handle corporate and personal data in accordance with the General Data Protection Regulation (GDPR), California Consumer Privacy Act (CCPA), and SOC2 Type II compliance standards.

---

## 2. Data We Process

### 2.1 Customer Source Code
- **Static AST Analysis:** Source code evaluated via CI/CD gates is analyzed in-memory or inside ephemeral containers.
- **Data Non-Retention Guarantee:** We **do not** permanently store raw repository code or training sets on our central servers. Only static AST violation metadata (line numbers, anti-pattern tags, score deductions) and energy telemetry metrics are saved.

### 2.2 Operational Telemetry & Identifiers
- User corporate email, name, role, and organization affiliation.
- Hardware telemetry (CPU cycles, RAPL energy in Joules, pod resource metrics).
- Git provenance (repository slug, commit SHA, PR number, branch name).

---

## 3. Security & Data Protection Controls
- **Encryption in Transit:** All network traffic is encrypted using TLS 1.3.
- **Encryption at Rest:** All credentials, tokens, and sensitive columns are encrypted via AES-256 / Fernet at rest.
- **Multi-Tenancy Isolation:** Logical row-level tenant boundary enforcement ensures zero cross-tenant data leakage.

---

## 4. Sub-processors
We use cloud infrastructure provided by Amazon Web Services (AWS) and Electricity Maps (grid carbon intensity telemetry). Both maintain ISO 27001 and SOC2 certifications.

---

## 5. Contact & Data Protection Officer
For data deletion requests, Data Protection Agreements (DPAs), or privacy inquiries:  
Email: `privacy@greencode.io`


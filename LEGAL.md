# ⚖️ GreenCode Enterprise Legal Framework

This document outlines the standard legal terms, commercial licensing, Data Processing Agreement (DPA), and Master Service Agreement (MSA) provisions for GreenCode Auditor deployments.

---

## 1. Master Service Agreement (MSA) Summary

### 1.1 Grant of License
Subject to the terms of this Agreement, GreenCode Auditor grants Customer a non-exclusive, non-transferable right to access and utilize the GreenCode energy profiling and verification software across authorized software engineering repositories.

### 1.2 Intellectual Property & Source Code Ownership
- **Customer IP:** Customer retains 100% full, exclusive ownership of all source code, proprietary algorithms, and repository artifacts audited by GreenCode. GreenCode claims zero copyright, license, or ownership over Customer code.
- **GreenCode IP:** The GreenCode Auditor parsing algorithms, mathematical formulas, and verification platform remain the intellectual property of GreenCode under Apache License 2.0 or commercial enterprise licensing terms.

### 1.3 Limitation of Liability
Except in cases of gross negligence or willful misconduct, neither party shall be liable for indirect, incidental, special, or consequential damages. In no event shall aggregate liability exceed the total amounts paid by Customer in the preceding twelve (12) months.

---

## 2. GDPR Data Processing Agreement (DPA)

### 2.1 Scope & Processing Details
- **Subject Matter:** Energy consumption auditing, AST pattern evaluation, and carbon footprint telemetry computation.
- **Categories of Data:** Developer commit metadata (committer name/email for energy attribution), API tokens for repository ingestion.
- **Data Deletion:** Upon contract termination, all customer credential tokens and non-aggregated audit records are permanently purged within thirty (30) calendar days.

### 2.2 Security Measures
Technical and organizational measures conform to the GreenCode Security Policy (`SECURITY.md`) and SOC 2 Trust Services Criteria (`.security/`).

---

## 3. Terms of Service & Acceptable Use Policy (AUP)
- Customers agree not to submit malicious software designed to compromise the sandboxed dynamic execution engine.
- Automated API abuse or denial of service against the reality verification pipeline will result in immediate IP and credential revocation.


# GreenCode Enterprise Architecture Blueprint

## 1. System Overview
GreenCode is a high-assurance, multi-tenant software energy and carbon gatekeeper designed for enterprise CI/CD and production Kubernetes clusters. It implements the Green Software Foundation Software Carbon Intensity (SCI) v1.0 specification and provides binding pre-deployment gate decisions to eliminate software carbon regressions before code reaches production.

```
                         [ GitHub / GitLab / Bitbucket CI/CD ]
                                         │
                                   Webhook / PR Gate
                                         ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                       GreenCode API Control Plane                      │
   │                                                                        │
   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐ │
   │  │ app.auth     │   │ app.tenants  │   │ app.policies │   │ app.audit│ │
   │  │ JWT/SSO/RBAC │   │ Org/Team/Proj│   │ Rules Engine │   │ AST/CST  │ │
   │  └──────────────┘   └──────────────┘   └──────────────┘   └──────────┘ │
   │                                                                        │
   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐ │
   │  │ app.energy   │   │ app.k8s      │   │ app.reports  │   │app.admin │ │
   │  │ RAPL/Cloud   │   │ Auto-Rollback│   │ CSRD / SEC   │   │ AuditLog │ │
   │  └──────────────┘   └──────────────┘   └──────────────┘   └──────────┘ │
   └────────────────────────────────────────────────────────────────────────┘
                    │                                      │
         PostgreSQL (Tenant-Isolated)             Redis (Token Revocation)
                    ▲                                      ▲
                    │                                      │
           Live Kubernetes Clusters               Electricity Maps API
         (Pod Telemetry & Rollback)             (Marginal Grid Emissions)
```

## 2. Core Pillars & Design Principles

### Multi-Tenancy & Data Isolation
- **Hierarchical Tenancy**: `Organization` -> `Team` -> `Project` -> `Repository`.
- **RBAC**: Strict role enforcement (`org_admin`, `team_lead`, `developer`, `auditor`, `viewer`).
- **Data Governance**: All metrics, budgets, and policies are strictly isolated by `org_id`.

### Calibrated Energy & Hardware Agnostic Modeling
- **Bare-Metal Linux**: Direct Intel/AMD RAPL hardware counters (`/sys/class/powercap`).
- **Cloud Hypervisors (AWS Graviton, Azure, GCP, K8s Pods)**: SPECpower_ssj2008 & Cloud Carbon Footprint (CCF) non-linear quadratic curve derivation based on active CPU utilization, memory residency, and datacenter PUE (1.15).
- **Statistical Confidence Scoring**: Provenance tracking tagging every calculation as `0.98` (RAPL direct) or `0.88` (calibrated cloud model) for auditor defense.

### Declarative Policy Engine
- **Pre-Deploy PR Gate**: Blocks pull requests if energy regressions exceed threshold (default 15-25%) or green score drops below 80.
- **Budget Thresholds**: Automated warnings at 70%, critical alerts at 90%, and hard merge blockers at 100% quota consumption.
- **Dirty Grid Awareness**: Postpones non-essential batch workloads during peak regional carbon intensity windows (>450 gCO2e/kWh).

### Production Kubernetes Auto-Rollback
- Monitors live pod Wattage against baseline deployment profiles.
- When an active deployment spikes power by >35% above baseline, the sentinel initiates an automated rollback via Kubernetes REST API and logs the event to the cryptographic audit trail.

### Cryptographic Audit Ledger & Compliance
- **SHA-256 Hash Chaining**: Every policy change, deployment gate decision, and rollback is cryptographically linked to the previous entry via hash chaining (`prev_hash` -> `record_hash`), ensuring tamper evidence for SOC 2 Type II and ISO 14064 audits.
- **Regulatory Disclosures**: Automated export of Scope 2 (operational) and Scope 3 Category 1/2 (embodied infrastructure) emissions formatted for CSRD ESRS E1 and SEC Climate Disclosures.


# GreenCode Architecture Specification

## 1. System Overview
GreenCode is a self-hosted software energy and carbon analysis platform for CI/CD pipelines, developer workflows, and MCP agents. It implements the Green Software Foundation Software Carbon Intensity (SCI) v1.0 formula (`SCI = (E * I + M) / R`) and provides pre-deployment gate evaluations to catch algorithmic energy regressions before code merges.

```
                         [ GitHub Actions / CI Runner / Alexa+ MCP ]
                                         │
                                  REST / MCP HTTP
                                         ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                       GreenCode FastAPI Service                        │
   │                                                                        │
   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐ │
   │  │ app.auth     │   │ app.services │   │ app.policies │   │app.parser│ │
   │  │ JWT / RBAC   │   │ Org/Team/Proj│   │ Rules Engine │   │ AST/CST  │ │
   │  └──────────────┘   └──────────────┘   └──────────────┘   └──────────┘ │
   │                                                                        │
   │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────┐ │
   │  │ app.energy   │   │ app.k8s      │   │ app.reports  │   │app.audit │ │
   │  │ Sensors/Model│   │ Rollback Svc │   │ ESG / SCI    │   │Hash Chain│ │
   │  └──────────────┘   └──────────────┘   └──────────────┘   └──────────┘ │
   └────────────────────────────────────────────────────────────────────────┘
                    │                                      │
         SQLite / PostgreSQL (SQLAlchemy)       Redis (Optional Cache/Revocation)
                    ▲                                      ▲
                    │                                      │
           Optional K8s API / kubectl             4-Tier Grid Carbon Chain
        (KUBERNETES_SERVICE_HOST / KUBECONFIG)  (UK ESO / ENTSO-E / EM / Static)
```

## 2. Core Subsystems & Provenance Guarantees

### Multi-Tenancy & RBAC (`app/services/org_service.py`, `app/auth/roles.py`)
- **Tenant Hierarchy**: `Organization` -> `Team` -> `Project` -> `Repository` stored via SQLAlchemy (SQLite by default for local/single-node runs; PostgreSQL supported via `DATABASE_URL`).
- **RBAC**: Application-level role checks (`superadmin`, `org_admin`, `team_lead`, `developer`, `auditor`, `viewer`) enforced via FastAPI dependencies (`require_permission`, `get_tenant_actor`).

### Energy Measurement & Calibrated Modeling (`app/energy_sensors.py`, `app/calibrated_energy.py`)
- **Bare-Metal Linux (`measurement_is_hardware: true`)**: Reads Intel/AMD RAPL counters (`/sys/class/powercap`), Scaphandre Prometheus metrics, `perf stat` PMU events, or `/sys/class/power_supply` discharge rates when available on the host.
- **Cloud & Hypervisor Estimation (`measurement_is_hardware: false`)**: When hardware counters are unavailable (such as on Windows, macOS, WSL2, or unprivileged cloud VMs), derives estimated energy using SPECpower and Cloud Carbon Footprint (CCF) power curves across AWS Graviton4 (`c8g`), AWS Inferentia2 (`inf2`), AWS Trainium1 (`trn1`), x86, and GPU profiles.
- **Strict Provenance**: Every response includes `measurement_method` and `measurement_is_hardware` so estimates are never misrepresented as physical hardware readings.

### Declarative Policy Engine (`app/services/energy_policy_service.py`, `app/services/budget_service.py`)
- **Pre-Deploy PR Gate**: Flags or blocks pull requests when estimated energy regressions exceed configured thresholds (default 15–25%) or when the static Green Score drops below threshold.
- **Team Carbon Budgets**: Tracks monthly team carbon allocations with configurable alert thresholds at 70% (`WARNING`), 90% (`CRITICAL`), and 100% (`BREACHED`).
- **Grid Carbon Awareness**: Evaluates regional grid carbon intensity (`gCO2e/kWh`) to advise delaying batch jobs when grid intensity exceeds configured thresholds.

### Kubernetes Energy Profiler & Rollback Controller (`app/kubernetes_profiler.py`, `app/services/rollback_service.py`)
- Compares pod wattage against registered baseline deployment profiles.
- When power spikes >35% above baseline:
  - If `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_ACCOUNT_TOKEN` are set, dispatches a live Kubernetes AppsV1 rollback (`is_live_cluster=True, execution_mode="k8s_api"`).
  - If `KUBECONFIG` is set and `kubectl` is installed, executes `kubectl rollout undo deployment/<name> -n <namespace>` (`is_live_cluster=True, execution_mode="kubectl"`).
  - Otherwise, records a simulated dry-run rollback decision (`is_live_cluster=False, execution_mode="simulated_dry_run"`) so local/CI tests never claim to have mutated a live cluster.

### Tamper-Evident Audit Trail & ESG Reporting (`app/audit_logs.py`, `app/reports/esg_report.py`)
- **SHA-256 Hash Chaining**: Every policy update, budget allocation, and rollback evaluation recorded via `AuditLogManager.record_event` commits to the previous record's SHA-256 digest (`prev_hash` -> `record_hash`), verified by `AuditLogManager.verify_integrity`.
- **SCI & GHG Disclosures**: Exports JSON, CSV, and printable HTML reports implementing the GSF SCI v1.0 formula and Scope 2 / Scope 3 calculation breakdowns. GreenCode is an engineering calculation tool and does not constitute an independent SOC 2 Type II or ISO 14064-1 certification audit.


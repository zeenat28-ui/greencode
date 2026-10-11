# GreenCode Architecture Overview

See full detailed architecture specifications in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Architecture Summary
GreenCode is a self-hosted software carbon and energy analysis service designed for CI/CD Pull Request gates, developer IDEs, and Alexa+ / MCP agent workflows.

### Implemented Subsystems
1. **Multi-Tenant Data Model & RBAC (`app/services/org_service.py`, `app/auth/roles.py`)**: SQLAlchemy models for `Organization`, `Team`, `Project`, and `User` with role-scoped permission checks (`superadmin`, `org_admin`, `team_lead`, `developer`, `auditor`, `viewer`).
2. **Hardware & Calibrated Energy Engine (`app/energy_sensors.py`, `app/calibrated_energy.py`)**: Reads hardware energy counters (`rapl`, `scaphandre`, `perf`, `battery`) on supported Linux hosts (`measurement_is_hardware=True`), and falls back to TDP/SPECpower-calibrated instance models (`AWS Graviton4`, `Inferentia2`, `Trainium1`, x86, GPU) with `measurement_is_hardware=False` on hypervisors without counter passthrough.
3. **Declarative Energy Policy Engine (`app/services/energy_policy_service.py`, `app/services/budget_service.py`)**: Evaluates pre-deployment energy regression limits, monthly team carbon budgets (70% warning / 90% critical / 100% breach), and regional grid intensity thresholds.
4. **Kubernetes Energy Profiler & Rollback Controller (`app/kubernetes_profiler.py`, `app/services/rollback_service.py`)**: Evaluates pod wattage against baseline profiles and triggers rollback when power spikes >35% above baseline. Reports explicit provenance (`is_live_cluster: bool` and `execution_mode: "k8s_api" | "kubectl" | "simulated_dry_run"`) depending on whether `KUBERNETES_SERVICE_HOST` / `KUBECONFIG` is configured.
5. **Pre-Deploy PR Energy Delta Gate (`app/services/energy_diff_service.py`)**: Compares base and head scans to generate Markdown PR gate comments with $\Delta\text{Energy}$, $\Delta\text{USD Cost}$, and $\Delta\text{CO}_2\text{e}$.
6. **Tamper-Evident Audit Trail & ESG Export (`app/audit_logs.py`, `app/reports/esg_report.py`)**: SHA-256 hash-chained SQLite/PostgreSQL audit log records (`AuditLogManager`) and JSON/HTML/CSV disclosures implementing the GSF SCI v1.0 formula.


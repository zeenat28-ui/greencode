# GreenCode Enterprise Architecture Blueprint

See full detailed architecture specifications in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Executive Architecture Summary
GreenCode provides an enterprise-scale software carbon and energy gatekeeper platform designed for Fortune 500 CI/CD pipelines and production Kubernetes clusters.

### Key Pillars
1. **Multi-Tenancy & RBAC**: Strict organizational, team, and project hierarchy with role-scoped permissions.
2. **Calibrated Energy Engine**: SPECpower & CCF calibrated hardware-agnostic energy derivation across AWS Graviton, Azure, GCP, and Kubernetes pods.
3. **Declarative Energy Policy Engine**: Enforces pre-deployment energy limits, carbon budgets (70%/90%/100%), and dirty grid windows.
4. **Automated Kubernetes Rollbacks**: Real-time pod energy tracking triggering automated rollback if deployment power spikes >35% above baseline.
5. **Pre-Deploy PR Energy Delta Gate**: AST diff comparison generating sticky GitHub comments with $\Delta\text{Energy}$, $\Delta\text{USD Cost}$, and $\Delta\text{CO}_2\text{e}$.
6. **Cryptographic Compliance Ledger**: SHA-256 hash-chained audit logs with regulatory export conforming to GHG Protocol, CSRD ESRS E1, and SEC Climate Disclosures.


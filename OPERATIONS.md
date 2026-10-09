# GreenCode Enterprise Operations, SLA & Runbook

See full operational specifications and disaster recovery runbooks in [docs/OPERATIONS.md](docs/OPERATIONS.md) and [docs/ops/](docs/ops/).

## Operations Summary
- **Target SLA**: 99.95% Availability.
- **Fail-Open Strategy**: Safeguards CI/CD from false-negative pipeline blocks.
- **Observability**: Real-time Prometheus metrics at `/metrics` and health checks at `/health` and `/api/admin/health`.
- **RTO & RPO**: <15 minutes RTO, <5 minutes RPO via automated multi-AZ database replication.


# GreenCode Enterprise Operations & Runbook

## Service Reliability & SLA
- **Target Uptime**: 99.95% availability for CI/CD webhook evaluation and control plane.
- **Fail-Open Policy for CI/CD**: In the event of temporary control plane degradation, GitHub Actions checks can be configured with `continue-on-error: true` or fallback to modeled offline AST evaluations so engineering deployments are never blocked by upstream network outages.

## Monitoring & Observability

### Prometheus Metrics Endpoints
Exported at `GET /metrics`:
- `greencode_http_requests_total`: Throughput by HTTP method and status code.
- `greencode_audits_total`: Total AST audits completed.
- `greencode_k8s_rollbacks_total`: Automated Kubernetes rollbacks executed.
- `greencode_carbon_avoided_kg_total`: Cumulative avoided carbon emissions.

### Health Probes
- **Liveness Probe**: `GET /health` -> 200 OK
- **Readiness Probe**: `GET /api/admin/health` -> checks DB connection and Redis health.

## High Availability & Disaster Recovery
- **Database Failover**: Managed via Amazon RDS Multi-AZ or Azure PostgreSQL Flexible Server with automated synchronous replication and <60s failover.
- **Ledger Backups**: Nightly encrypted snapshots with 30-day point-in-time recovery (PITR).
- **Disaster Recovery RTO & RPO**:
  - Recovery Time Objective (RTO): < 15 minutes.
  - Recovery Point Objective (RPO): < 5 minutes.


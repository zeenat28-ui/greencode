# GreenCode Operations & Observability Guide

## CI/CD Gate Execution & Fail-Open Option
- **Standalone CLI Gate**: `python -m app.main --path . --threshold 75 --ci` runs locally inside any CI runner without requiring an external server.
- **Fail-Open Option for Remote Webhook Calls**: When invoking remote HTTP endpoints from CI/CD, GitHub Actions steps can be configured with `continue-on-error: true` or fall back to local CLI execution so builds are not blocked by network outages.

## Monitoring & Observability Endpoints

### Prometheus Metrics (`GET /metrics`)
Exported at `GET /metrics` (`app/observability.py`):
- `greencode_http_requests_total`: HTTP request counter by method, path, and status code.
- `greencode_audits_total`: Total static/dynamic code audits completed.
- `greencode_k8s_rollbacks_total`: Kubernetes rollback evaluations triggered.
- `greencode_carbon_avoided_kg_total`: Cumulative modeled carbon reductions.

### Health & Security Probes
- **Primary Health & Provenance Endpoint**: `GET /api/health` -> returns service status (`healthy` or `degraded`), secret configuration checks, and carbon intensity provider verification status (`verified_live: bool`).
- **Liveness Probe**: `GET /health` -> `200 OK`.
- **Admin Readiness Probe**: `GET /api/admin/health` -> checks database connectivity.

## Database & Ledger Persistence (Self-Hosted)
- **Database Backend**: Uses SQLite (`greencode.db`) by default for zero-dependency local execution, or PostgreSQL when `DATABASE_URL` is configured (see `docker-compose.yml`).
- **Tamper-Evident Ledgers**: Verify audit chain integrity at any time via `GET /api/reports/audit-logs/{org_id}/verify` and `GET /api/pipeline/ledger/verify`.


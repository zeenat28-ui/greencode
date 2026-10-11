# GreenCode Operations & Observability Overview

See full operational details in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Operational Summary
- **Health & Security Probes**: `GET /api/health` (full security & carbon provider provenance status), `GET /health`, and `GET /api/admin/health`.
- **Prometheus Metrics**: Exported at `GET /metrics` for scraping by Prometheus/Grafana (`deploy/prometheus.yml`).
- **CI/CD Gate Execution**: Runs standalone via `python -m app.main --path . --threshold 75 --ci` or via GitHub Actions (`action.yml`).
- **AWS Operations CLI**: `python -m app.aws_cli` integrates with AWS SSM Parameter Store, CloudWatch Logs, EventBridge, S3, and X-Ray when AWS credentials are configured.


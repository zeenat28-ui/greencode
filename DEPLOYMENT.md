# GreenCode Deployment Overview

See full deployment instructions in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Included Deployment Manifests
1. **Docker Compose (`docker-compose.yml`, `deploy/docker-compose.prod.yml`)**: Multi-container stack (FastAPI backend, Nginx/React frontend, PostgreSQL, Redis, optional Scaphandre sidecar).
2. **Kubernetes Helm Chart (`deploy/helm/greencode`)**: Reference Helm chart templates (`deployment.yaml`, `service.yaml`, `hpa.yaml`, `pvc.yaml`) for Kubernetes clusters.
3. **Terraform Templates (`deploy/terraform`)**: Reference infrastructure templates for cloud provisioning.


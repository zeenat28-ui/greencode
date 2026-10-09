# GreenCode Enterprise Deployment Playbook

See full deployment and cloud guide in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Quick Deployment Paths
1. **Kubernetes (Helm)**: Production deployment via `deploy/helm/greencode` with PVC, HPA, and RBAC support.
2. **Multi-Cloud IaC (Terraform)**: Automated AWS (Graviton3 RDS/Redis), Azure, and GCP provisioning in `deploy/terraform`.
3. **Docker Compose**: High-availability multi-container stack in `deploy/docker-compose.prod.yml`.


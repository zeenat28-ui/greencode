# GreenCode Self-Hosted Deployment Guide

## Deployment Options Included in This Repository

### 1. Docker Compose (Recommended for Local & Single-Host)
Runs the FastAPI backend, React frontend, PostgreSQL, and Redis (`docker-compose.yml` or `deploy/docker-compose.prod.yml`):

```bash
cp .env.example .env
# Populate JWT_SECRET, POSTGRES_PASSWORD, REDIS_PASSWORD, SECRETS_ENCRYPTION_KEY in .env
docker compose up -d --build
```

### 2. Kubernetes Helm Chart (`deploy/helm/greencode`)
Reference Helm chart templates for deploying GreenCode on Kubernetes clusters (EKS, AKS, GKE, or local `kind`/`minikube`):

```bash
cd deploy/helm/greencode

helm upgrade --install greencode . \
  --namespace greencode \
  --create-namespace \
  --set env.jwtSecret="<STRONG_JWT_SECRET>" \
  --set env.databaseUrl="postgresql://user:pass@postgres-host:5432/greencode" \
  --set env.redisUrl="redis://redis-host:6379/0"
```

### 3. Reference Terraform Templates (`deploy/terraform`)
Starter Infrastructure-as-Code templates for cloud environments:

```bash
cd deploy/terraform
terraform init
terraform plan -var="environment=production" -var="cloud_provider=aws"
```

## Security & Secrets Configuration
1. **JWT_SECRET**: Required in `ENV=production` (`python -c "import secrets; print(secrets.token_urlsafe(48))"`).
2. **SECRETS_ENCRYPTION_KEY**: Used by `app/database.py` to encrypt stored GitHub tokens at rest via **Fernet (AES-128-CBC with HMAC-SHA256)**.
3. **Database TLS**: When connecting to external PostgreSQL instances over untrusted networks, configure `sslmode=verify-full` in `DATABASE_URL`.
4. **Kubernetes Rollback Credentials**: Live cluster rollback in `app/kubernetes_profiler.py` requires either in-cluster `KUBERNETES_SERVICE_HOST` + `KUBERNETES_SERVICE_ACCOUNT_TOKEN` or a configured `KUBECONFIG` with `kubectl`; otherwise rollbacks run in `simulated_dry_run` mode (`is_live_cluster=False`).


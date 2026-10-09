# Enterprise Deployment Guide

## Overview
GreenCode Gatekeeper can be deployed across three standard enterprise deployment targets:
1. **Docker Compose (Single-Host / Evaluation / Self-Hosted)**
2. **Kubernetes via Helm (Production Multi-Node / Multi-Cloud)**
3. **AWS EKS / ECS Fargate with Amazon Bedrock Integration**

---

## 1. Quickstart: Self-Hosted Docker Compose

```bash
# Clone the repository
git clone https://github.com/zeenat28-ui/greencode.git
cd greencode

# Copy and configure enterprise secrets
cp .env.example .env
# Ensure SECRETS_ENCRYPTION_KEY and JWT_SECRET are at least 32 random characters

# Launch the full enterprise stack
docker compose -f deploy/docker-compose.prod.yml up -d
```

Verify the deployment:
```bash
curl http://localhost:8000/api/health
```

---

## 2. Production Kubernetes Deployment via Helm

```bash
# Add GreenCode Helm repository or use local chart
cd deploy/helm/greencode

# Install into dedicated namespace
helm upgrade --install greencode . \
  --namespace greencode-system \
  --create-namespace \
  --values values.yaml \
  --set env.SECRETS_ENCRYPTION_KEY="<32-byte-base64-key>" \
  --set env.JWT_SECRET="<long-random-jwt-secret>"
```

### In-Cluster Kubernetes Rollback Permissions
Ensure the ServiceAccount has permission to read and rollback deployments:
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: greencode-rollback-controller
rules:
  - apiGroups: ["apps"]
    resources: ["deployments", "deployments/rollback"]
    verbs: ["get", "list", "patch", "update"]
```

---

## 3. GitHub Actions CI/CD Pre-Deploy Gate Integration

Add to `.github/workflows/greencode-gate.yml`:
```yaml
name: GreenCode Energy Gate
on: [pull_request]

jobs:
  energy-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run GreenCode Gate
        run: |
          pip install -r requirements.txt
          python -m app.main --path . --threshold 80
```


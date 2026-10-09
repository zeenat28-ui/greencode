# GreenCode Enterprise Deployment Guide

## Production Architecture Options

### 1. Kubernetes Deployment (Helm)
The recommended deployment model for Fortune 500 enterprises running on Amazon EKS, Azure AKS, or Google GKE.

```bash
# Add Helm chart directory
cd deploy/helm/greencode

# Customize values
helm upgrade --install greencode . \
  --namespace greencode \
  --create-namespace \
  --set env.jwtSecret="<ENTERPRISE_STRONG_JWT_SECRET>" \
  --set env.databaseUrl="postgresql://user:pass@rds-endpoint:5432/greencode" \
  --set env.redisUrl="rediss://elasticache-endpoint:6379/0"
```

### 2. Multi-Cloud Terraform Provisioning
Provisions low-carbon ARM64 (AWS Graviton3 / Azure Ampere) infrastructure:

```bash
cd deploy/terraform
terraform init
terraform apply -var="environment=production" -var="cloud_provider=aws"
```

### 3. Production Docker Compose
For dedicated on-premise or edge instances:

```bash
docker compose -f deploy/docker-compose.prod.yml up -d
```

## Security & Secrets Checklist
1. **JWT_SECRET**: Must be cryptographically generated (`openssl rand -hex 32`) and stored in AWS Secrets Manager or HashiCorp Vault.
2. **SECRETS_ENCRYPTION_KEY**: Required to encrypt customer GitHub tokens and OAuth secrets in PostgreSQL using AES-256-GCM.
3. **Database TLS**: Enforce `sslmode=verify-full` on all RDS/PostgreSQL connections.
4. **Kubernetes RBAC**: Ensure the GreenCode ServiceAccount is restricted to authorized namespaces for rollback actions.


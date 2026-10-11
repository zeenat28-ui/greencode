# GreenCode Terraform Infrastructure Templates

This directory provides multi-cloud Terraform templates for deploying GreenCode with PostgreSQL replication, Redis caching, and ARM64 / Graviton compute instances.

## Supported Clouds
- **AWS**: Multi-AZ RDS PostgreSQL (Graviton3), Redis ElastiCache replication group, Application Load Balancer.
- **Azure**: Azure PostgreSQL Flexible Server, Azure Cache for Redis, Resource Groups.
- **GCP**: Cloud SQL PostgreSQL HA Regional Cluster.

## Quick Start
```bash
terraform init
terraform plan -var="environment=production"
terraform apply -var="environment=production"
```

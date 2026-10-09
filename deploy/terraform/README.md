# GreenCode Enterprise Terraform Infrastructure as Code

This directory provides audited, multi-cloud Infrastructure as Code (IaC) templates for deploying GreenCode in enterprise environments with high availability, database replication, and low-carbon compute architecture (ARM64 / Graviton).

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


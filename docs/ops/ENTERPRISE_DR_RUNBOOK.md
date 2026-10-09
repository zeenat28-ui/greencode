# GreenCode Enterprise Disaster Recovery, High Availability & Operational Runbook

## 1. High Availability (HA) Architecture Summary
GreenCode is deployed across 3 Availability Zones (AZs) with:
- **Compute Tier**: Kubernetes Pods autoscaling from 3 to 10 replicas with PodDisruptionBudgets (`minAvailable: 2`).
- **Database Tier**: AWS Aurora PostgreSQL Serverless v2 with automatic cross-AZ replication and sub-30 second failover.
- **Cache/Session Tier**: AWS ElastiCache Redis multi-AZ with automatic failover enabled.

## 2. Recovery Time & Point Objectives (RTO / RPO)
- **Target RTO (Recovery Time Objective)**: < 15 minutes for complete regional failover.
- **Target RPO (Recovery Point Objective)**: < 1 minute (WAL streaming to S3 with point-in-time recovery enabled).

## 3. Automated Database Backup & Verification Procedures

### Daily Automated Snapshot
```bash
# Verify Aurora / Postgres automated snapshot retention (minimum 30 days retained)
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier greencode-enterprise-cluster \
  --snapshot-type automated
```

### Manual Disaster Recovery Restore Procedure
1. Create new Aurora cluster from point-in-time snapshot:
   ```bash
   aws rds restore-db-cluster-to-point-in-time \
     --source-db-cluster-identifier greencode-enterprise-cluster \
     --db-cluster-identifier greencode-dr-cluster \
     --restore-to-time 2026-10-09T18:00:00Z \
     --db-subnet-group-name greencode-db-subnets
   ```
2. Update Kubernetes Secret with new endpoint:
   ```bash
   kubectl set env deployment/greencode-enterprise-deployment \
     DATABASE_URL="postgresql+asyncpg://app_user:vault_secret@greencode-dr-cluster.cluster.rds.amazonaws.com:5432/greencode_enterprise"
   ```

## 4. Hash-Chained Audit Ledger Verification & Tamper Recovery
GreenCode writes tamper-evident audit receipts for all energy scans:
```bash
# Verify ledger integrity
python -c "from app.pipeline import ledger; assert ledger.verify_chain() == True, 'Tampering detected'"
```

## 5. Service Level Objectives (SLOs) & Alert Thresholds
| Metric | SLO Target | Alerting Threshold | Escalation Action |
| :--- | :--- | :--- | :--- |
| **API Availability** | 99.9% Uptime | < 99.8% over 15 min | PagerDuty SEV-1 to On-Call Lead |
| **P95 Latency (Audit API)** | < 350 ms | > 600 ms for 5 min | Scale replica pods + Inspect DB pool |
| **P95 Latency (MCP Alexa+)** | < 450 ms | > 500 ms (Alexa SLA budget) | Warm cache & recycle idle uvicorn workers |
| **Database Connection Pool** | < 75% utilized | > 85% pool exhaustion | Increment DB_POOL_SIZE / Aurora scale |

# Enterprise Disaster Recovery & Business Continuity Plan

## 1. RPO & RTO Objectives
- **Recovery Point Objective (RPO):** **< 15 minutes** (maximum tolerable data loss window)
- **Recovery Time Objective (RTO):** **< 30 minutes** (maximum tolerable time to restore full service)

---

## 2. High Availability Architecture
1. **Multi-AZ Kubernetes Clusters:** Gatekeeper pods are distributed across 3 distinct Availability Zones with pod anti-affinity.
2. **PostgreSQL High Availability:** Primary database replicated asynchronously to a hot standby in an alternate zone with automated failover via Patroni/RDS Multi-AZ.
3. **Stateless Workloads:** All core API services are stateless. Session tokens and rate limit tracking are backed by Redis with persistence.

---

## 3. Backup Schedule & Verification
- **Continuous WAL Archival:** PostgreSQL write-ahead logs streamed continuously to immutable cloud storage.
- **Daily Full Snapshots:** Automated nightly snapshots encrypted at rest with AES-256 and stored with WORM protection.
- **Bi-Weekly Recovery Drills:** SRE team performs automated sandbox restoration drills bi-weekly to ensure backup viability.

---

## 4. Failover Procedure
1. SRE on-call receives automated pager alert regarding primary zone outage.
2. Promote secondary PostgreSQL read replica to primary.
3. Update Kubernetes ConfigMap `DATABASE_URL` via GitOps / ArgoCD.
4. Execute `kubectl rollout restart deployment/greencode-gatekeeper -n greencode-system`.
5. Verify health check `GET /api/health` returns `200 OK`.


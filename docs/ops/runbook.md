# GreenCode Enterprise Operational Runbook

## Overview
This runbook guides Site Reliability Engineers (SREs) and DevOps operators in managing the GreenCode Gatekeeper platform in production.

---

## 1. Architecture & Core Services
- **API Gatekeeper:** FastAPI asynchronous service running under Uvicorn (`app/main.py`)
- **Database:** PostgreSQL 16 with async connection pool (`app/database.py`)
- **Queue/Cache:** Redis 7 for rate-limiting, job dispatch, and session token caching
- **Kubernetes Profiler & Rollback Controller:** In-cluster sentinel monitoring pod energy and triggering rolling rollbacks on energy regression spikes (`app/kubernetes_profiler.py`, `app/services/rollback_service.py`)

---

## 2. Health Probes & Monitoring
- **Liveness & Readiness Endpoint:** `GET /api/health`
  - Returns `200 OK` with database connection state, Celery worker status, and Fernet encryption status.
- **Prometheus Metrics:** `GET /metrics`
  - Scraped by Prometheus on port 8000. Tracks request latency, carbon budget quota violations, and rollback events.

---

## 3. Incident Triage & Response

### Alert: `CRITICAL_ENERGY_SPIKE` (>35% regression)
1. **Trigger:** Automatic canary rollback triggered by Sentinel controller.
2. **Action:**
   - Verify deployment status: `kubectl rollout status deployment/<deployment-name> -n <namespace>`
   - Inspect rollback audit logs: `curl -H "Authorization: Bearer $TOKEN" https://greencode.internal/api/reports/audit-logs/1?action=k8s:rollback_evaluation`
   - Notify team lead of blocked regression.

### Alert: `CARBON_BUDGET_BREACHED` (>=100% quota)
1. **Trigger:** Team carbon consumption exceeds monthly allocation.
2. **Action:**
   - Query team status: `curl https://greencode.internal/api/budgets/status/<team-slug>`
   - If emergency deployment is required, execute authorized admin override via `POST /api/energy/policy`.

---

## 4. Disaster Recovery & Database Failover
- **Daily Automated Backups:** PostgreSQL pg_dump snapshot retained for 30 days in encrypted S3/GCS.
- **Failover:** Automated read-replica promotion with RPO < 15 minutes, RTO < 30 minutes.
- Detailed DR steps: see [`DISASTER_RECOVERY.md`](file:///C:/Users/Zeenat/Desktop/greencode/DISASTER_RECOVERY.md).


# Enterprise Incident Response Protocol

## 1. Scope & Triage Hierarchy
This incident response protocol defines the procedures for triaging, mitigating, and documenting operational and security incidents across GreenCode Enterprise Gatekeepers.

---

## 2. Severity Classification Matrix

| Severity | Incident Description | First Response | Escalation Channel |
| :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Automated Kubernetes rollback failure, CI/CD pipeline deadlock | **< 15 minutes** | PagerDuty SRE Lead, VP Engineering |
| **SEV-2 (Major)** | Unplanned carbon budget breach without automated warning, Redis outage | **< 1 hour** | On-call Platform Engineer |
| **SEV-3 (Minor)** | Diagnostic reporting discrepancy, UI latency degradation | **< 4 hours** | SRE Slack channel |

---

## 3. Incident Lifecycle Phases

```
+---------------------------------------------------------------------------------+
| Detection --> Triage --> Containment --> Remediation --> Post-Mortem & Evidence |
+---------------------------------------------------------------------------------+
```

### Phase 1: Detection & Automated Containment
- When a pod energy spike exceeds 35%, `KubernetesEnergyMonitor` emits a `CRITICAL_SPIKE` verdict.
- Automated API rollback dispatches `PATCH /apis/apps/v1/.../rollback` to restore the last known healthy replica set.
- An immutable SHA-256 event is appended to the audit ledger.

### Phase 2: Containment & Isolation
- If manual intervention is required, SREs trigger:
  ```bash
  curl -X POST https://greencode.internal/api/energy/rollback \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"namespace": "production", "deployment_name": "payments-api", "current_power_w": 300, "baseline_power_w": 150}'
  ```

### Phase 3: Post-Incident Review & Audit Preservation
- Generate incident audit ledger export:
  `GET /api/reports/audit-logs/{org_id}?action=k8s:rollback_evaluation`
- Document root cause analysis (RCA) and verify hash chain integrity via `GET /api/reports/audit-logs/{org_id}/verify`.


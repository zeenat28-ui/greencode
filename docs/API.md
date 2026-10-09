# GreenCode Enterprise API Reference

## Authentication & Multi-Tenancy

### Register Tenant Organization
`POST /api/auth/register`
```json
{
  "email": "lead@company.com",
  "username": "lead_engineer",
  "password": "SecurePassword123!",
  "org_name": "Acme Global",
  "org_slug": "acme-global"
}
```
**Response (201 Created):**
```json
{
  "user": { "id": 1, "email": "lead@company.com", "role": "org_admin" },
  "organization": { "id": 1, "name": "Acme Global", "slug": "acme-global" },
  "tokens": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "def502...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

### Organization & Team Management
- `GET /api/tenants/orgs` - List tenant workspaces.
- `GET /api/tenants/orgs/{org_id}` - Retrieve tenant quotas.
- `POST /api/tenants/orgs/{org_id}/teams` - Create engineering team with carbon quota.
- `POST /api/tenants/orgs/{org_id}/projects` - Register monitored microservice or service.

---

## Energy & Carbon Policies

### Get / Update Policy
- `GET /api/policies/{org_id}` - Fetch active organizational guardrail rules.
- `POST /api/policies/{org_id}` - Update thresholds (`max_regression_pct`, `breach_threshold_pct`, `auto_rollback_k8s`).

### Evaluate Deployment Rules
`POST /api/policies/evaluate`
```json
{
  "org_id": 1,
  "current_energy": 0.18,
  "baseline_energy": 0.12,
  "team_budget_consumed": 420.0,
  "team_budget_total": 500.0,
  "grid_intensity": 380.0
}
```
**Response:**
```json
{
  "decision": "BLOCK",
  "is_blocked": true,
  "regression_pct": 50.0,
  "team_budget_consumed_pct": 84.0,
  "violations": [
    "Deployment energy regression +50.0% exceeds threshold (25.0%)"
  ],
  "warnings": [
    "Team carbon budget warning (84.0% consumed, warning threshold is 70.0%)"
  ]
}
```

---

## CI/CD PR Energy Gate

### Compare Pull Request Analysis
`POST /api/pr-gate/compare`
```json
{
  "base_scan": { "total_energy_joules": 0.05, "green_score": 92.0 },
  "head_scan": { "total_energy_joules": 0.065, "green_score": 84.0 },
  "max_regression_pct": 15.0
}
```
**Response:**
```json
{
  "verdict": "BLOCKED",
  "is_blocked": true,
  "energy_delta_pct": 30.0,
  "energy_delta_joules": 0.015,
  "annual_cost_delta_usd": 5400.0,
  "annual_carbon_delta_kg": 1260.0,
  "pr_markdown_comment": "### 🔴 FAILED - MERGE BLOCKED..."
}
```

---

## Kubernetes Sentinel & Rollback

### Evaluate Live Power Spike
`POST /api/kubernetes/evaluate-rollback`
```json
{
  "namespace": "production",
  "deployment_name": "payments-svc",
  "current_power_w": 380.0,
  "baseline_power_w": 220.0,
  "auto_trigger": true
}
```
**Response:**
```json
{
  "deployment": "production/payments-svc",
  "spike_pct": 72.73,
  "verdict": "CRITICAL_SPIKE",
  "rollback_triggered": true,
  "rollback_status": { "status": "SUCCESS" }
}
```

---

## Compliance & ESG Reports

- `GET /api/reports/esg/{org_id}` - Scope 2 & 3 emissions JSON summary.
- `GET /api/reports/esg/{org_id}/html` - Audit-grade executive HTML certificate.
- `GET /api/reports/esg/{org_id}/csv` - SEC Climate Disclosure tabular export.
- `GET /api/admin/audit-logs/{org_id}` - Immutable hash-chained audit records.
- `GET /api/admin/audit-logs/{org_id}/verify` - Cryptographic SHA-256 chain verification.


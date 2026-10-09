# Enterprise Data Retention and Pruning Protocol

## 1. Compliance Standard
This protocol enforces data hygiene conforming to GDPR Article 5(1)(e) (storage limitation), SOC2 Trust Criteria CC6.5, and ISO 14064 GHG audit requirements.

---

## 2. Retention Lifecycles

```
+-----------------------------------+--------------------+------------------------+
| Data Asset                        | Retention Window   | Disposition Action     |
+-----------------------------------+--------------------+------------------------+
| Cryptographic Audit Records       | 7 Years (WORM)     | Legal Hold / Archive   |
| Deployment Energy & SCI Metrics   | 3 Years            | Aggregated rollups     |
| AST Scan File Detections          | 90 Days            | Automated Prune        |
| OAuth Tokens & Secrets            | Active Session     | Scrubbed on Revocation |
+-----------------------------------+--------------------+------------------------+
```

---

## 3. Automated Pruning Job
The data retention lifecycle is enforced programmatically via:
```python
from app.compliance import ComplianceManager
ComplianceManager.enforce_data_retention(retention_days=365)
```
This is executed as a scheduled Kubernetes CronJob running daily at `00:00 UTC`.


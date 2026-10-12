# Data Retention & Pruning Guide

## 1. Overview
GreenCode stores scan summaries, carbon budget metrics, and hash-chained audit logs in the configured SQLAlchemy database (`app/database.py`), while parsing source code in memory without persisting raw customer source files to the database.

---

## 2. Recommended Retention Windows (Self-Hosted Policy Template)

```
+-----------------------------------+--------------------+------------------------+
| Data Table / Asset                | Recommended Window | Disposition Action     |
+-----------------------------------+--------------------+------------------------+
| AuditLog (Hash-Chained Records)   | 1 - 7 Years        | Retain for audit trail |
| AuditRecord / CarbonBudget        | 1 - 3 Years        | Retain or export CSV   |
| Violation (Per-Scan Detections)   | 90 - 365 Days      | Prune via helper       |
| RefreshToken                      | 7 Days TTL         | Revoked on rotation    |
+-----------------------------------+--------------------+------------------------+
```

---

## 3. Programmatic Retention Helper (`app/compliance.py`)
Operators can invoke the built-in retention helper in [`app/compliance.py`](app/compliance.py) via Python or a scheduled cron/systemd timer on their host:
```python
from app.compliance import ComplianceManager
result = ComplianceManager.enforce_data_retention(retention_days=365)
print(result)
```


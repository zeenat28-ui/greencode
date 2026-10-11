# Self-Hosted Backup & Recovery Runbook

> **Scope Note:** This document provides a reference backup and recovery runbook for teams self-hosting GreenCode with Docker Compose (`docker-compose.yml`), PostgreSQL (`DATABASE_URL`), or SQLite (`greencode.db`).

## 1. Stateless & Stateful Components
1. **Stateless API & MCP Services (`app/main.py`, `app/mcp_server.py`):** Can be restarted or redeployed from container images at any time without local state loss.
2. **Database (`SQLite` or `PostgreSQL`):** Stores historical scan metrics, carbon budgets, and hash-chained `AuditLog` entries (`app/database.py`).
3. **Pipeline Ledger (`app/pipeline/ledger.py`):** Append-only JSONL ledger file (configurable via `GREENCODE_LEDGER_PATH`).

---

## 2. Backup Procedures (Self-Hosted)
- **PostgreSQL (`docker-compose.yml`):**
  ```bash
  docker compose exec db pg_dump -U greencode greencode > greencode_backup_$(date +%F).sql
  ```
- **SQLite (Local / Single-Node):**
  ```bash
  sqlite3 greencode.db ".backup 'greencode_backup.db'"
  ```
- **S3 Evidence Upload (`app/aws_cli.py`):**
  Signed audit reports can be archived to Amazon S3 using:
  ```bash
  python -m app.aws_cli s3 push report.json
  ```

---

## 3. Recovery & Integrity Verification Procedure
1. Restore the PostgreSQL dump or SQLite backup file.
2. Run database schema migrations:
   ```bash
   alembic upgrade head
   ```
3. Start the application stack and verify health:
   ```bash
   docker compose up -d
   curl http://localhost:8000/api/health
   ```
4. Verify cryptographic hash-chain continuity of restored audit logs:
   ```bash
   curl http://localhost:8000/api/reports/audit-logs/1/verify
   curl http://localhost:8000/api/pipeline/ledger/verify
   ```


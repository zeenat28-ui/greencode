# GreenCode Secrets Rotation Runbook

**Audience:** Self-Hosted Operators & Security Engineers

## 1. Scope
GreenCode reads its secrets from the environment (`.env`, Docker Compose, Helm values, or your secret manager) at process start; none are transmitted anywhere. This runbook covers rotating each of them, the blast radius of each rotation, and how to verify the result. Rotate immediately on suspected exposure or staff departure - never wait for the cadence.

---

## 2. Secret Inventory

| Secret | Read by | Blast radius if leaked | Rotation impact |
|---|---|---|---|
| `JWT_SECRET` | `app/core/config.py` (`resolve_jwt_secret`) | Forge valid access/refresh tokens - full API impersonation | Every session invalidated; users re-login |
| `SECRETS_ENCRYPTION_KEY` | `app/database.py` (Fernet at rest) | Decrypt every stored GitHub PAT from a DB dump | **Must** go through `scripts/rekey_secrets.py`, or stored tokens strand |
| `DATABASE_URL` (DB password) | `app/database.py` | Full read/write of tenants, repositories, audit ledgers | Short connection cutover |
| `REDIS_PASSWORD` | queue / token-revocation paths | Inject or clear revocation entries | Brief in-memory fallback during cutover |
| Third-party keys (`HUGGINGFACE_API_KEY`, carbon-intensity keys, `GITHUB_TOKEN`) | feature clients | Abuse of the upstream account | Feature-scoped only; no stored data affected |

`.env` is git-ignored - if a secret was ever committed, treat it as leaked and rotate it even after removal from history.

---

## 3. Rotation Procedures

### 3.1 JWT_SECRET
1. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` (≥ 48 characters; anything under 32 is rejected in production).
2. Update the environment and restart the service (rolling restart is fine, but keep the window short - instances on the old key reject tokens minted on the new one).
3. Verify: `GET /api/health` → `security.jwt_secret_configured: true`, `security.jwt_secret_blockers: []`, `deps.jwt_secret: "ok"`.
4. Announce that all users must re-login; refresh tokens are signed with the same key, so there is no graceful handover.

### 3.2 SECRETS_ENCRYPTION_KEY
Never swap only the env var: tokens already on disk were sealed with the **old** key, `decrypt_secret` returns undecryptable input unchanged, and the failure surfaces later as an unexplained GitHub 401 on every scan.

1. Drain maintenance traffic (writes between the rekey and the restart are sealed with the old key - see step 5).
2. Set the new key for the rekey run, and expose the old one alongside:
   ```bash
   export SECRETS_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
   export OLD_SECRETS_ENCRYPTION_KEY=<previous value>   # prefer env over --old-key (ps visibility)
   ```
3. Dry run (writes nothing): `python scripts/rekey_secrets.py`
4. Apply: `python scripts/rekey_secrets.py --apply`
   - Rows decryptable by **neither** key are left untouched and reported; the script exits non-zero (`1`) so a pipeline halts. Fix those before discarding the old key.
   - Exit `2` means the current key is not configured at all.
5. Re-run the dry run to catch rows written during the window; repeat until it reports `0 would re-encrypt`.
6. If plaintext rows are reported, run `python scripts/migrate_plaintext_secrets.py --apply`.
7. Restart the service onto the new key, then remove `OLD_SECRETS_ENCRYPTION_KEY` from the environment.
8. Verify: `GET /api/health` → `security.credential_encryption_configured: true`, `plaintext_tokens_pending_migration: 0`.

### 3.3 PostgreSQL and Redis Credentials
- **PostgreSQL**: `ALTER ROLE greencode_admin WITH PASSWORD '<new>';` → update `DATABASE_URL` → rolling restart. Verify `/api/health` shows `deps.database: "ok"` and, in production, `deps.database_backend: "ok"` (a production host on SQLite is reported as degraded and refused at boot when `DATABASE_REQUIRE_POSTGRES=1`).
- **Redis**: `CONFIG SET requirepass '<new>'` (or an ACL `SETUSER` rotation) → update `REDIS_URL` → rolling restart. Until every instance has the new password, token-revocation falls back to per-instance in-memory state, so keep the cutover window short.

### 3.4 Third-Party Keys
Update the environment variable and restart. No data migration; verify via `deps.huggingface` / `deps.carbon_intensity` on `/api/health`.

---

## 4. Verification Checklist
- [ ] `curl -s localhost:8000/api/health | jq .security` → every `*_configured` is `true` and every `*_blockers` list is `[]`.
- [ ] `plaintext_tokens_pending_migration` is `0` and `database_backend_blockers` is `[]`.
- [ ] `rekey_secrets.py` dry run reports `0 would re-encrypt`; `migrate_plaintext_secrets.py` reports nothing pending.
- [ ] Old key material removed from the environment, secret manager, and CI variables.
- [ ] Rotation recorded in your change log (who, when, which secret - never the value).

---

## 5. Cadence
- **JWT_SECRET**: at least every 90 days, plus immediately on suspected exposure or staff departure.
- **SECRETS_ENCRYPTION_KEY**: at least annually; run the rekey procedure for every rotation.
- **Database / Redis credentials**: per organizational policy, ideally with automated rotation.
- **Any secret that touched version control**: rotate first, investigate second.

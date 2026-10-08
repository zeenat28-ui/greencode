# SOC 2 Trust Services Criteria: Access Control Policy (CC6.1 - CC6.3)

## 1. Purpose & Scope
This policy defines the technical controls and administrative procedures governing user and machine access to GreenCode Auditor systems, databases, and APIs.

## 2. Principle of Least Privilege
- **Role-Based Access Control (RBAC):** Access rights are granted based on explicit user roles (`admin`, `engineer`, `auditor`, `viewer`).
- **Default Deny:** All unauthenticated API endpoints (except `/api/health` and `/api/pipeline/status`) deny access by default (HTTP 401 Unauthorized).
- **Service Accounts:** Automated CI/CD workers and external runners interact exclusively through short-lived JWT tokens or HMAC-SHA256 request signatures.

## 3. Secret & Credential Management
- **No Plaintext Storage:** GitHub personal access tokens, database connection strings, and webhook secrets are encrypted at rest with Fernet cryptographic keys.
- **Environment Isolation:** Secrets are injected strictly through validated environment variables (`.env`) and are rejected if found in version control.
- **Fail-Closed Runtime Guards:** If `JWT_SECRET` is unset, too short (<32 bytes), or matches a public template default, the FastAPI application immediately terminates with `RuntimeError`.


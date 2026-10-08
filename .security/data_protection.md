# SOC 2 Trust Services Criteria: Data Protection & Privacy (CC6.6 - CC6.8)

## 1. Data Classification
- **Confidential / Restricted:** GitHub OAuth tokens, API secrets, private repository source code, user passwords.
- **Internal / Audit:** Energy measurement logs, verification ledgers, historical Green Scores.
- **Public:** Documentation, open-source AST parsing rules, ESG certificate templates.

## 2. Encryption at Rest & In Transit
- **In Transit:** TLS 1.3 encryption enforced across all external endpoints. Plain HTTP is rejected or redirected.
- **At Rest:** Database fields storing sensitive credentials utilize AES-128-CBC encryption with HMAC validation.
- **Ephemeral Sandbox Storage:** Sandboxed code checkouts are written to volatile tmpfs mounts and completely scrubbed upon container exit.

## 3. GDPR & Data Subject Rights
- GreenCode does not monetize or transfer personal data.
- User accounts and audit telemetry may be purged upon verified request via the data retention APIs.


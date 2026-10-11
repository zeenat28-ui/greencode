# Privacy Policy — GreenCode Auditor (Self-Hosted & Alexa+ MCP Add-On)

**Effective Date:** January 1, 2026  
**Last Updated:** October 2026

## 1. Overview
GreenCode Auditor is an open-source (Apache-2.0) software energy and carbon analysis tool and self-hosted Alexa+ MCP Server (`/privacy` endpoint required by [`alexa/addon.json`](alexa/addon.json)). This policy describes what data the application processes when run locally or via a self-hosted tunnel.

---

## 2. Data Processed by the Application

### 2.1 Source Code Snippets & Repository Scans
- **In-Memory Static Analysis (`app/parser.py`):** Source code submitted for static AST/CST analysis is parsed in memory to compute violation line numbers, Green Scores, and SCI estimates. Raw source code files are not stored in the database.
- **Optional LLM Refactoring (`app/bedrock_client.py`, `app/huggingface_client.py`):** Only when explicitly invoked (e.g., via `refactor_code` with `GREENCODE_LLM_PROVIDER` configured), the flagged function snippet is sent to the operator's configured Amazon Bedrock or HuggingFace account. When unconfigured, refactoring runs 100% locally via deterministic AST rules.

### 2.2 Operational & Audit Metadata (`app/database.py`)
- User account identifiers (email, username, role, organization ID) when multi-tenant authentication is enabled.
- Scan summary metrics (Green Score, energy in Joules, SCI score, violation counts) and SHA-256 hash-chained `AuditLog` entries.

---

## 3. Credential Storage & Security Controls
- **Encryption at Rest:** Stored credentials (such as GitHub Personal Access Tokens) are encrypted using **Fernet (AES-128-CBC with HMAC-SHA256)** when `SECRETS_ENCRYPTION_KEY` is configured (`app/database.py`).
- **Loopback Binding by Default:** Container ports in `docker-compose.yml` bind to `127.0.0.1` by default.

---

## 4. External APIs (Optional / Operator-Configured)
- **Grid Carbon Intensity (`app/sci.py`):** Queries public UK National Grid ESO (`api.carbonintensity.org.uk`) or operator-configured ENTSO-E / Electricity Maps / WattTime keys, falling back to a bundled offline dataset when offline.
- **AWS Integration (`app/bedrock_client.py`, `app/aws_cli.py`):** Connects to the operator's own AWS account via standard `boto3` credentials when enabled.

---

## 5. Contact & Repository
For privacy questions or issues regarding this open-source project, open an issue on [`https://github.com/zeenat28-ui/greencode`](https://github.com/zeenat28-ui/greencode).


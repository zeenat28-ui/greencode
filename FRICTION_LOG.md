# AWS & Alexa+ MCP Integration Engineering Log — GreenCode

Documented field notes, root-cause diagnostics, and engineering resolutions encountered while building and hardening the GreenCode Alexa+ MCP server, OAuth 2.1 (RFC 9728) transport layer, and AWS Bedrock Converse API integration.

---

## 1. `aws` command not resolved immediately after installing AWS CLI v2 on Windows

- **Symptom:** Installed `AWSCLIV2.msi`, ran `aws --version` in an already-open PowerShell session, and received `The term 'aws' is not recognized as the name of a cmdlet...`.
- **Root Cause:** The MSI installs `C:\Program Files\Amazon\AWSCLIV2\aws.exe` and updates the machine-level `PATH` registry key, but active PowerShell processes retain the environment block inherited from their parent process at launch.
- **Resolution:** Reload the session environment or invoke `app/aws_cli.py`, which resolves `shutil.which("aws")` first and automatically falls back to standard Windows MSI installation paths (`%ProgramFiles%\Amazon\AWSCLIV2\aws.exe`) when the shell `PATH` has not yet been refreshed.
- **Verification:**
  - `python -c "from app.aws_cli import find_aws_executable; print(find_aws_executable())"` resolves the binary deterministically across interactive and non-interactive shells.

## 2. Decoupling self-hosted Alexa+ MCP servers from AWS CodeArtifact CLI credentials

- **Symptom:** Running `npm install -g @alexa-ai/cli` from the default public npm registry returns `HTTP 404` because `@alexa-ai/cli` is distributed via a private AWS CodeArtifact repository that requires `aws codeartifact login` (whose authorization token expires every 12 hours).
- **Root Cause:** `@alexa-ai/cli` is required only when deploying Amazon-hosted MCP lambdas into AWS infrastructure; self-hosted HTTPS MCP servers communicate directly with the Alexa+ cloud router over Streamable HTTP (`2025-11-25`) and OAuth 2.1.
- **Resolution:** Architected GreenCode as a self-contained, self-hosted Streamable HTTP MCP server (`app/mcp_server.py`) paired with a validated `alexa/addon.json` manifest and automated compliance verifiers (`check_mcp_alexa.py`, `check_mcp_live.py`). In addition, `app/bedrock_client.py` lazy-loads `boto3` and degrades gracefully to the deterministic AST refactoring engine when AWS credentials are not provisioned.
- **Verification:**
  - `python check_mcp_live.py` boots an ephemeral loopback server and verifies the full JSON-RPC 2.0 handshake, tool discovery, and live tool execution (`ALL LIVE MCP CHECKS PASSED`) without requiring external cloud billing.

## 3. Dynamic tunnel domain rotation in `alexa/addon.json`

- **Symptom:** Ephemeral Cloudflare tunnels (`*.trycloudflare.com`) assign a new subdomain on every restart, invalidating the MCP endpoint URI, OAuth privacy/terms URLs, and icon URLs in `alexa/addon.json`.
- **Root Cause:** Self-hosted add-on manifests require absolute HTTPS URIs that match the active ingress hostname.
- **Resolution:** `scripts/start_mcp_remote.ps1` parses the newly assigned tunnel hostname from `cloudflared` output on startup, atomically updates all endpoint and asset URLs inside `alexa/addon.json`, and registers the hostname in `GREENCODE_MCP_ALLOWED_HOSTS`. For permanent production deployments, a named Cloudflare tunnel or dedicated TLS domain can be supplied via environment configuration.

## 4. Streamable HTTP transport returning `HTTP 421 Misdirected Request` behind reverse proxies

- **Symptom:** Forwarding external HTTPS traffic to `/mcp` returned `421 Misdirected Request` prior to reaching the OAuth 2.1 bearer gate.
- **Root Cause:** The Python MCP Streamable HTTP transport enforces strict `Host` header validation (`127.0.0.1` / `localhost` by default) to prevent DNS-rebinding attacks.
- **Resolution:** Configured dynamic `Host` allow-listing in `app/mcp_server.py` driven by `GREENCODE_MCP_ALLOWED_HOSTS`, and updated `scripts/start_mcp_remote.ps1` to inject the active ingress hostname automatically.

## 5. Capturing `cloudflared` ingress URLs from `stderr`

- **Symptom:** Redirecting only `stdout` from `cloudflared tunnel --url ...` produced an empty log file while waiting for the public tunnel URL.
- **Root Cause:** `cloudflared` writes all structured lifecycle logs—including the generated `https://<subdomain>.trycloudflare.com` banner—to `stderr`.
- **Resolution:** Updated `scripts/start_mcp_remote.ps1` to capture both `stdout` and `stderr` streams (`RedirectStandardError`) and match `https://[a-z0-9-]+\.trycloudflare\.com` deterministically.

## 6. Amazon-hosted (`regionalEndpoints`) vs. self-hosted (`integrations[0].type = "MCP"`) manifest schemas

- **Symptom:** Sample screenshots from the Alexa+ developer portal show `mcpServer` and `regionalEndpoints` pointing to `execute-api.*.amazonaws.com`, which differs from the self-hosted add-on schema.
- **Root Cause:** `regionalEndpoints` is populated internally by Amazon API Gateway when Amazon hosts the backend skill. Self-hosted MCP servers must declare `integrations[0].type = "MCP"` with `config.endpoints.default.uri` pointing to the external HTTPS `/mcp` endpoint.
- **Resolution:** Codified the 37-point self-hosted manifest schema check in `tests/test_alexa_compliance.py` and `vfy/check_manifest.py`.
- **Verification:**
  - `python vfy/check_manifest.py --manifest alexa/addon.json` validates all required schema keys, HTTPS URIs, and OAuth metadata alignments.

## 7. PowerShell argument quoting with inline Python invocations

- **Symptom:** Multi-line `powershell -Command "python -c \"...\""` invocations failed with syntax errors (`Missing expression after ','` or `Missing closing ')'`).
- **Root Cause:** PowerShell performs `$`-variable interpolation and quote unescaping before passing arguments to the child Python process.
- **Resolution:** Standardized all verification routines as standalone, idempotent Python modules under `vfy/` (`vfy/baseline_check.py`, `vfy/check_manifest.py`, `vfy/verify_submission.py`).

## 8. End-to-end Alexa+ MCP protocol verification without regional mobile app dependencies

- **Symptom:** The Alexa mobile companion app is geo-restricted in several regional app storefronts, and voice routing requires an `en-US` marketplace profile.
- **Root Cause:** Regional storefront distribution policies restrict mobile client downloads outside supported territories.
- **Resolution:** Built `check_mcp_alexa.py` to execute the complete Alexa+ cloud router compliance suite directly against the live HTTPS `/mcp` endpoint—verifying `HTTP 401` unauthenticated rejection with `WWW-Authenticate: Bearer resource_metadata=...`, RFC 9728 Protected Resource Metadata (`/.well-known/oauth-protected-resource`), OAuth 2.0 Authorization Server Metadata (`/.well-known/oauth-authorization-server` with `S256` PKCE), DNS-rebinding rejection (`HTTP 421`), and sub-500ms JSON-RPC tool execution latency.
- **Verification:**
  - `python check_mcp_alexa.py --url <endpoint> --token $env:GREENCODE_MCP_TOKEN`

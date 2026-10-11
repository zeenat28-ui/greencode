# Deploying the GreenCode MCP Server to a Persistent HTTPS Host

Alexa+ requires the remote MCP server to be reachable on a **persistent HTTPS URL**. A `cloudflared` quick tunnel is ephemeral — it stops when the local host sleeps or the network drops.

This directory contains a lightweight deployment of the MCP service (`app/mcp_server.py` and the analysis modules it imports). It runs inside a ~338 MB container image and passes the Alexa+ MCP compliance checks:

| Endpoint | Expected | Status |
|---|---|---|
| `GET /privacy` | `200` | Verified `200` |
| `GET /mcp` (no token) | `401`, no `WWW-Authenticate` | Verified `401` |
| `GET /.well-known/oauth-protected-resource` | `200`, resource ends `/mcp` | Verified |
| `GET /.well-known/oauth-authorization-server` | `200`, PKCE `S256` | Verified |

The image fits inside a 512 MB instance (such as Render's free plan), whereas the full root `Dockerfile` bundles FastAPI, Streamlit, and multi-language runtime toolchains.

## Files

- `mcp/Dockerfile.mcp` — copies `app/` and `alexa/`, installs `deploy/mcp/requirements-mcp.txt`, and listens on `$PORT`.
- `mcp/requirements-mcp.txt` — minimal runtime dependencies for the MCP server.
- `../render.yaml` — Render Blueprint specification.

## Deploy to Render

1. Push this repository to GitHub.
2. In the Render Dashboard, select **New** -> **Blueprint** and choose `zeenat28-ui/greencode`. Render reads `render.yaml` and creates the `greencode-mcp` web service.
3. After the initial deployment completes, note the public service URL (e.g., `https://greencode-mcp.onrender.com`).
4. Set **`GREENCODE_MCP_ALLOWED_HOSTS`** in the Render dashboard to that exact hostname (no scheme, no trailing slash) so the MCP transport's DNS-rebinding guard permits requests to that host.
5. Copy the generated **`GREENCODE_MCP_TOKEN`** from the Render environment tab for client authentication and verification checks.

## Keep-Alive Configuration (Free Tier)

Free web services on Render spin down after ~15 minutes of inactivity. To prevent cold-start latency on incoming Alexa+ voice requests, configure an external health check probe against `/privacy` every 10 minutes (for example via `cron-job.org` or an uptime monitor).

## Verify the Deployment

```bash
GREENCODE_MCP_TOKEN=<token> python vfy/verify_submission.py
python check_mcp_live.py
python check_mcp_alexa.py
```

## Update `alexa/addon.json`

Update all `https://<old-host>` URLs in `alexa/addon.json` to match your deployed HTTPS hostname so that the endpoint URI, OAuth metadata, privacy/terms links, and icons share the same domain:

```powershell
(Get-Content alexa/addon.json -Raw) `
  -replace 'https://[a-z0-9-]+\.trycloudflare\.com', 'https://greencode-mcp.onrender.com' |
  Set-Content alexa/addon.json
```

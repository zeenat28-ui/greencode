# Deploying the GreenCode MCP server to a stable host

The Alexa+ submission needs the MCP server reachable on a **stable HTTPS URL**
for the whole judging window (9–20 Nov). A `cloudflared` quick tunnel is
ephemeral — it dies when your laptop sleeps or the network drops, and a judge
hitting a dead URL sees a 404.

This folder holds a slim, free-tier deployment of **only the MCP surface**
(`app/mcp_server.py` + the engine it imports). It has been built and run in a
container locally and passes the full Alexa+ compliance checklist:

| Endpoint | Expected | Verified |
|---|---|---|
| `GET /privacy` | `200` | ✅ 200 |
| `GET /mcp` (no token) | `401`, **no** `WWW-Authenticate` | ✅ 401, no header |
| `GET /.well-known/oauth-protected-resource` | `200`, resource ends `/mcp` | ✅ |
| `GET /.well-known/oauth-authorization-server` | `200`, PKCE `S256` | ✅ |

The image is ~338 MB (verified by a local `docker build`), so it fits Render's
free instance (512 MB RAM). The full `Dockerfile` at the repo root builds the
entire product (FastAPI + Streamlit UI + Node/Java/Go toolchains) and does
**not** fit comfortably there.

## Files

- `Dockerfile.mcp` — slim image; copies only `app/` and `alexa/`, installs the
  minimal runtime (`requirements-mcp.txt`), listens on `$PORT`.
- `../requirements-mcp.txt` — the exact packages the MCP server imports.
- `../../render.yaml` — Render Blueprint (New → Blueprint → this repo).

## Deploy to Render (free, no credit card)

1. Push this repo to GitHub (Render builds from the repo).
2. Render Dashboard → **New** → **Blueprint** → select `zeenat28-ui/greencode`.
   Render reads `render.yaml` and creates a `greencode-mcp` web service.
3. After the first deploy, note the public URL, e.g.
   `https://greencode-mcp.onrender.com`.
4. **Set `GREENCODE_MCP_ALLOWED_HOSTS`** in the Render dashboard to that exact
   public host (no scheme, no trailing slash). If it does not match, the MCP
   SDK's DNS-rebinding guard answers the public URL with `421`.
5. Read back the generated **`GREENCODE_MCP_TOKEN`** from the dashboard — you
   need it to run the checkers.

## Keep the free instance awake (critical for judging)

Render free web services **sleep after ~15 minutes of no traffic** and take up to
a minute to wake. During judging that cold-start looks like downtime. Pin the
service so it never sleeps:

1. Create a free account at <https://cron-job.org> (no card).
2. New cron job → URL `https://greencode-mcp.onrender.com/privacy`, schedule
   **every 10 minutes**. `/privacy` is public, returns 200, and is cheap — the
   ideal keep-alive probe.
3. Leave it active through 20 Nov.

## Verify the live deployment

```bash
# Replace the host with your Render URL, and the token with the dashboard value.
GREENCODE_MCP_TOKEN=<token> python vfy/verify_submission.py
# or the focused MCP/Alexa checkers:
python check_mcp_live.py
python check_mcp_alexa.py
```

## Point addon.json at the new host

`alexa/addon.json` still points at the last `trycloudflare.com` tunnel. Update
every `https://<old>.trycloudflare.com` to your Render host, then commit. The
verifier enforces that **all** URLs share one domain, so change them together.

```bash
# Example (PowerShell) — review the diff before committing:
(Get-Content alexa/addon.json -Raw) `
  -replace 'https://[a-z0-9-]+\.trycloudflare\.com', 'https://greencode-mcp.onrender.com' |
  Set-Content alexa/addon.json
```

## Alternative hosts

Any host that runs a long-lived web process on a stable HTTPS URL works — Amazon
does not care where it is hosted. Same Dockerfile, same env vars
(`GREENCODE_MCP_TOKEN`, `GREENCODE_MCP_ALLOWED_HOSTS=<host>`, `PORT`).

- **SnapDeploy** — free, no card, South-Asia friendly; deploy from the Dockerfile.
- **Railway** — free trial (~30 days), no card; may expire before judging ends.
- **Vercel** — *not* recommended: its functions are stateless/serverless, which
  fits the React frontend but not a long-running MCP server with sessions. Fine
  for hosting `frontend/`, wrong for the MCP service.

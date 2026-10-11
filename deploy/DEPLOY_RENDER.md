# Deploying the GreenCode MCP Server to Render

This guide deploys the GreenCode MCP server (`app/mcp_server.py`) to a persistent HTTPS endpoint on Render using `render.yaml` and `deploy/mcp/Dockerfile.mcp`.

---

## 0. Why a Separate MCP Image

The root `Dockerfile` builds the full application stack (FastAPI + Streamlit + multi-language toolchains). `deploy/mcp/Dockerfile.mcp` builds only the MCP server and static analysis engine (~338 MB image), allowing it to run comfortably on a 512 MB instance:

```
python:3.12-slim  ->  pip install deploy/mcp/requirements-mcp.txt  ->  copy app/ + alexa/
```

| Check | Result |
|---|---|
| `/mcp` with no token | `401` with no `WWW-Authenticate` header |
| `/.well-known/oauth-protected-resource` (RFC 9728) | `200`, `resource` ends `/mcp` |
| `/privacy`, `/terms` | `200` |
| `tools/list` over Streamable HTTP | returns all 9 tools |
| MCP protocol version | `2026-07-28` (min required `2025-11-25`) |

## 1. Push the Repository

```bash
git add deploy/ render.yaml
git commit -m "feat(deploy): slim MCP image and Render blueprint"
git push origin main
```

## 2. Create the Blueprint Service

1. Open Render Dashboard -> **New** -> **Blueprint**.
2. Connect the `zeenat28-ui/greencode` repository. Render reads `render.yaml` and provisions `greencode-mcp`.
3. Click **Create Blueprint Service**.

## 3. Environment Configuration

After the first deployment completes:

- Copy the generated **`GREENCODE_MCP_TOKEN`** from the environment dashboard.
- Confirm the service URL (e.g., `https://greencode-mcp.onrender.com`).
- Ensure **`GREENCODE_MCP_ALLOWED_HOSTS`** matches the public hostname (without `https://`) so the MCP DNS-rebinding guard allows incoming requests.

## 4. Preventing Cold Starts on Free Instances

Render free instances spin down after ~15 minutes of inactivity. Configure an external HTTP `GET` monitor against `https://greencode-mcp.onrender.com/privacy` on a 10-minute interval to keep the worker warm and maintain `< 500 ms` MCP response times.

## 5. Verify Live and Update `alexa/addon.json`

```powershell
$env:GREENCODE_MCP_TOKEN = "<token>"
python vfy/verify_submission.py
```

Once verified, update all domain references in `alexa/addon.json` to `https://greencode-mcp.onrender.com` and commit.

## 6. Register Endpoint in Alexa+ Developer Console

Configure `https://greencode-mcp.onrender.com/mcp` as the MCP server URI in your Alexa+ Add-on manifest, and manage `GREENCODE_MCP_TOKEN` via the Render environment dashboard.

---

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Public `/mcp` returns `421` | `GREENCODE_MCP_ALLOWED_HOSTS` does not match public host | Set it to the service hostname in the Render dashboard |
| First request takes ~60s | Free instance was idle | Configure a 10-minute health check against `/privacy` |
| Build fails on `tree-sitter` | Missing prebuilt wheel for target architecture | Use `x86_64` Linux (`manylinux` wheels included for cp312) or add a compiler build stage |
| `/mcp` returns `401` | Bearer token missing | Send `Authorization: Bearer $GREENCODE_MCP_TOKEN` |

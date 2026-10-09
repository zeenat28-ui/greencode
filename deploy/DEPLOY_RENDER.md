# Deploy the GreenCode MCP server to Render (free, no card)

This gets the Alexa+ track a **stable public HTTPS URL** that stays live through
the judging window (9–20 Nov). A `trycloudflare` quick tunnel dies the moment
your laptop sleeps; a Render web service does not — provided you keep it awake
(step 4).

No credit card is required for the free instance type.

---

## 0. Why a separate slim image

The root `Dockerfile` builds the whole product (FastAPI + Streamlit) and installs
Node, a JRE, Go, gcc and every dependency. It does not fit comfortably on a
512 MB free instance.

`deploy/mcp/Dockerfile.mcp` builds **only** the Alexa+ MCP surface:

```
python:3.12-slim  ->  pip install deploy/mcp/requirements-mcp.txt  ->  copy app/ + alexa/
```

It is verified: the image builds to **~338 MB** and the container passes every
Alexa+ checklist item locally:

| Check | Result |
|---|---|
| `/mcp` with no token | `401` with **no** `WWW-Authenticate` header |
| `/.well-known/oauth-protected-resource` (RFC 9728) | `200`, `resource` ends `/mcp` |
| `/privacy`, `/terms` | `200` |
| `tools/list` over Streamable HTTP | returns all **9** tools |
| MCP protocol version | `2026-07-28` (min required `2025-11-25`) |

## 1. Push this repo

```bash
git add deploy/ render.yaml
git commit -m "feat(deploy): slim MCP image + Render blueprint for stable Alexa+ URL"
git push origin main
```

Render deploys from GitHub, so the deploy files must be on `origin` first.

## 2. Create the service (Blueprint)

1. Render Dashboard → **New** → **Blueprint**.
2. Connect the `zeenat28-ui/greencode` repo. Render reads `render.yaml` and
   proposes one service, `greencode-mcp`. **No credit card is required.**
3. **Create Blueprint Service**. The first build runs the slim Dockerfile.

## 3. Read back the values the checkers need

After the first deploy (Dashboard → `greencode-mcp`):

- **`GREENCODE_MCP_TOKEN`** was auto-generated. Copy it.
- **Service URL** will be `https://greencode-mcp.onrender.com`.

> If you later change the service name, update `GREENCODE_MCP_ALLOWED_HOSTS` in
> the dashboard to the new host. If it does not match the public host, the MCP
> SDK's DNS-rebinding guard answers the public URL with **421**.

## 4. Keep it awake (the one free-tier catch)

Render free **web services spin down after ~15 minutes** of no traffic and take
~1 minute to wake. During judging that cold start is a bad first impression, so
point a free external pinger at the public `/privacy` page every 10 minutes:

1. Go to **cron-job.org** (free, no card) → create a monitor.
2. URL: `https://greencode-mcp.onrender.com/privacy`, method `GET`.
3. Schedule: every **10 minutes**, 24×7.

That keeps a single free instance warm. Keep it running until judging closes.

## 5. Verify live, then update addon.json

```bash
# from a fresh clone, with the token from step 3
$env:GREENCODE_MCP_TOKEN = "<token>"
python vfy/verify_submission.py
```

All tunnel checks should now hit Render instead of `trycloudflare`. When green:

1. Point `alexa/addon.json` URLs at `https://greencode-mcp.onrender.com` (the
   verifier requires a **single** tunnel/host domain across all URLs).
2. Commit and push — same flow you already used for the previous tunnel swap.

## 6. Record the final host in the submission

Put `https://greencode-mcp.onrender.com` in the Devpost description and demo, and
note that `GREENCODE_MCP_TOKEN` is in the Render dashboard for anyone who wants
to run the checkers.

---

### Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Public `/mcp` returns **421** | `GREENCODE_MCP_ALLOWED_HOSTS` ≠ public host | Set it to the service host in the dashboard |
| First request slow (~1 min) | Free instance was asleep | Set up the cron-job.org pinger (step 4) |
| Build fails on `tree-sitter` | no prebuilt wheel for this platform/arch | the slim image ships **no** compiler by design: `pip --prefer-binary` picks the cp312 manylinux wheel (it exists for x86_64). On an unusual arch, add a compiler stage instead of assuming `build-essential` is present |
| `401` but judges expect tools | token missing | send `Authorization: Bearer $GREENCODE_MCP_TOKEN` |

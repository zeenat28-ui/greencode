# GreenCode Alexa+ Demo and ASK Integration

Self-hosted MCP server, Alexa+-style local web simulator, and a separate ASK
Custom Skill webhook for GreenCode Auditor.

## Architecture Overview

```
┌─────────────┐     POST /alexa/skill      ┌──────────────┐
│   Alexa     │ ────────────────────────▶  │  FastAPI     │
│   Skill     │                          │  Webhook     │
└─────────────┘                          └──────┬───────┘
                                                │
              ┌───────────────────┼─────────────┼─────────────┐
              ▼                   ▼             ▼             ▼
       ┌──────────┐       ┌──────────┐   ┌──────────┐  ┌──────────┐
       │ AlexaNLP │       │ Responses│   │ MCPTool  │  │ Auth     │
       │ Mapper   │       │ (SSML)   │   │ Executor │  │ Manager  │
       └──────────┘       └──────────┘   └──────────┘  └──────────┘
              │                   │             │             │
              ▼                   ▼             ▼             ▼
       ┌──────────┐       ┌──────────┐   ┌──────────┐  ┌──────────┐
       │ MCP/HTTP │       │  Core    │   │  Bedrock │  │  GitHub  │
       │ Transport│       │ Engine   │   │  Client  │  │ Client   │
       └──────────┘       └──────────┘   └──────────┘  └──────────┘
```

## No-cost hackathon web demo

The standalone simulator at `http://localhost:5173/alexa-demo` is the
recommended judge/demo path. It follows the web-based simulator approach used
by other Alexa+ hackathon projects: the browser is the user-facing simulator
and sends real MCP requests to GreenCode's self-hosted local MCP server. It
does not require an Amazon account, Alexa Developer Console, Echo, public
endpoint, GitHub sign-in, or payment card.

Start the MCP server and frontend in separate terminals from the repository
root:

```powershell
# Terminal 1
$env:GREENCODE_MCP_PORT = "8766"
python -m app.mcp_server

# Terminal 2
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Open `http://localhost:5173/alexa-demo` and choose one of its presets. The
simulator performs MCP initialize, tools/list, and tools/call requests; its
displayed results are tool responses, not scripted Alexa answers. Use
`http://localhost:5173/dashboard` for the same cockpit inside the signed-in
application.

**What this demonstrates:** a working browser-based Alexa+-style experience
using GreenCode's self-hosted MCP tools, suitable for the hackathon's own-web
simulator/front-end demo approach.

**What it does not demonstrate:** an Amazon-hosted Alexa+ invocation, a
Developer Console simulator result, or a physical Echo interaction. Those are
separate integrations and have not been verified. No public MCP URL is
configured in the checked-in add-on manifest.

## Optional external Alexa deployment requirements

The rest of this guide covers optional connection to Amazon's hosted services,
not prerequisites for the local hackathon demo:

- **Alexa Skill ID:** `GREENCODE_ALEXA_SKILL_ID` (Amazon Developer Console)
- **API Base URL:** Public HTTPS server reachable by Alexa's cloud service
- **GitHub Token:** Optional per-request GitHub token for repository auditing

The MCP bearer-token check is not an OAuth authorization-code/account-linking
implementation. Do not configure Alexa+ account linking against this endpoint
until a real authorization server is implemented and tested. Keep any public
MCP deployment protected by an appropriate authentication layer.

> **Credential setup:** See [`docs/API_KEYS.md`](../docs/API_KEYS.md) for
> signup links, required scopes, and environment variable names.

## Deploying

### 1. Deploy the API

```bash
# Run the FastAPI backend on port 8000 and the frontend using the repository's
# local development instructions. The in-browser microphone uses the local
# `/api/voice/alexa/ask` route; it does not need a public tunnel.
```

For Echo or Alexa Developer Console testing against the local backend, Alexa's
cloud service needs a public HTTPS URL. A local process by itself is not
reachable by Amazon. Use ngrok's free account development domain: it provides
a stable assigned hostname, so you do not need to buy or manage a domain.

```powershell
winget install --id Ngrok.Ngrok -e
.\scripts\setup-alexa-tunnel.ps1
```

Create a free ngrok account at [ngrok signup](https://dashboard.ngrok.com/signup)
and get its agent token from the [ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken).
Setup prompts for the token locally using a hidden input and saves it in ngrok's
user-level config, not the repository. Never send the token in chat or commit
it.
To rotate the local token after revoking an exposed one, run
`.\scripts\setup-alexa-tunnel.ps1 -ResetToken` and enter the replacement at
the hidden local prompt.

Start the complete local API, Alexa bridge, and tunnel together:

```powershell
.\scripts\start-alexa-local.ps1
```

The launcher starts the backend if needed, the restricted bridge, the ngrok
tunnel, the MCP Streamable HTTP server on port 8766, and the frontend if its
dependencies are installed. The dashboard proxies `/mcp` to that live server;
the Alexa tunnel remains restricted to the ASK webhook. It keeps the services
running until you press Ctrl+C. Existing services that it did not start are
left running. Logs for services started by the launcher are written under
`%LOCALAPPDATA%\GreenCode\logs`.

The bridge exposes only `POST /api/alexa/skill`; it does not expose the rest of
the local backend. The launcher remembers the assigned ngrok hostname and
requests the same hostname on later runs. If ngrok reports that the hostname
is unavailable, verify the account status and update the saved hostname in
`%LOCALAPPDATA%\GreenCode\alexa-tunnel.json`.

### Dashboard MCP demo

For an in-dashboard version of the local simulator, use the signed-in
GreenCode dashboard's **Alexa+ MCP web demo** panel. It speaks MCP Streamable HTTP directly: the
browser initializes a session, requests `tools/list`, and invokes `tools/call`
through `/mcp`. In local development, Vite proxies that path to the self-hosted
MCP server on `127.0.0.1:8766`. This demo does not use the ASK webhook or
`/api/voice/ask`; those are separate Alexa/voice paths. The Alexa Developer
Console Test tab is not used for this MCP workflow.

The region comparison and sample-code audit presets return actual MCP tool
results. Energy measurement provenance and grid-data source tiers are shown
in the response; a static reference reading is not presented as live telemetry.
The refactor preset prefers Amazon Bedrock by default, can fail over to
configured Gemini or Hugging Face providers, and reports the provider actually
used along with verification failures rather than claiming an unverified patch
was produced.

### Configure the Alexa+ MCP add-on

`alexa/addon.json` is the Alexa+ MCP add-on manifest. Its endpoint must be the
public Streamable HTTP MCP route ending in `/mcp`; it must not point at the ASK
Custom Skill webhook (`/api/alexa/skill`). Configure a public HTTPS origin
before deploying the add-on:

```powershell
# For a local MCP server exposed through a Cloudflare quick tunnel:
$env:GREENCODE_MCP_PORT = "8766"
$env:GREENCODE_MCP_TOKEN = "<set a local secret in this shell>"
$env:GREENCODE_ALEXA_SKILL_ID = "<the ASK skill ID from Developer Console>"
.\scripts\start_mcp_remote.ps1

# For an already deployed MCP server; also configure the separate ASK webhook:
.\scripts\configure-alexa-addon.ps1 -BaseUrl "https://mcp.example.com" -ConfigureAskSkill
alexa-ai deploy
```

The tunnel launcher writes the active HTTPS origin into `addon.json`, including
the `/mcp` endpoint and service-hosted privacy, terms, and image URLs. Quick
tunnel hostnames change when restarted; reconfigure the manifest and update
the Alexa+ integration whenever the URL changes. It also sets `alexa/skill.json`
to the separate `/api/alexa/skill` ASK webhook. Configure the Developer Console
Custom Skill endpoint to that URL while the tunnel is running. Do not use the
old Vercel site as the MCP host: that deployment does not include the MCP
transport.

`GREENCODE_MCP_TOKEN` protects the MCP transport, but GreenCode does not yet
implement an OAuth authorization/token flow for Alexa account linking. A
token-protected endpoint is suitable for the local MCP compliance checker and
clients that can supply a bearer token; do not expect Alexa+ to authenticate
to it until account linking is implemented. For an Alexa+ invocation, use an
explicitly authorized public endpoint and configure the authentication method
supported by the Alexa+ integration.

The repository manifest uses GitHub-hosted URLs for listing assets and policy
pages so these resources are available without an MCP server. The configure
script switches them to the MCP origin for tunnel-based development.

The Alexa+ MCP endpoint and ASK Custom Skill endpoint are separate integrations:
the MCP add-on uses `alexa/addon.json` and `/mcp`; the ASK skill uses
`alexa/skill.json` and `/api/alexa/skill`.

### 2. Configure the Alexa Skill

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Create a new skill: "GreenCode Auditor"
3. Choose "Custom" and "Skill Builder"
4. Set Invocation Name: `green code auditor`
5. Import interaction model from `alexa/interactionModels/custom/en-US.json`
6. Set HTTPS Endpoint to the stable URL printed by the launcher:
   `https://alexa.example.com/api/alexa/skill`.
7. Select the SSL certificate type that matches the endpoint certificate:
   - For the ngrok `*.ngrok-free.dev` hostname, select **My development
     endpoint is a sub-domain of a domain that has a wildcard certificate from
     a certificate authority**.
   - For a dedicated hostname with its own CA-signed certificate, select
     **My development endpoint has a certificate from a trusted certificate
     authority**.
8. Set the Skill ID to the exact ID shown for this skill in the console and
   set the same value in `GREENCODE_ALEXA_SKILL_ID`.
9. Save the endpoint and build the model. The stable endpoint does not need to
   be changed on later local runs. Test in the console's Test tab or on an Echo
   using the same Amazon account and region with the skill enabled for
   development.

Alexa account linking is not configured. The skill can answer project questions
from documentation and run supported grid lookups, but it cannot see the
dashboard's selected GitHub repository or audit private repositories. Run
repository scans, source-code refactors, SLA evaluations, and IaC audits from
the authenticated GreenCode dashboard with the actual repository or source
files selected.

The Alexa Developer Console simulator has its own browser microphone control.
Allow microphone access for `developer.amazon.com` in the browser and use a
supported browser; the simulator may not have microphone/AVS access inside a
VS Code embedded browser. This is separate from GreenCode's local voice
assistant, which asks for microphone permission after you select **Start
hands-free**.

The ASK webhook rejects requests without a valid `SignatureCertChainUrl` and
`Signature-256` signature, a fresh request timestamp, and the configured Skill
ID. The signature is verified against the exact request body; do not disable
these checks for local tunneling. The browser microphone is separate and uses
`/api/voice/alexa/ask`.

### 3. Set Environment Variables

```bash
GREENCODE_ALEXA_SKILL_ID=amzn1.ask.skill.ccf7d912-329a-4831-bf94-fb7a23d7471e
GREENCODE_MCP_TOKEN=your-mcp-secret-token
# Webhook abuse protection: max requests per client address per window
GREENCODE_ALEXA_RATE_LIMIT=100
GREENCODE_ALEXA_RATE_WINDOW_SECONDS=60
```

### 4. Deploy addon.json (Alexa+)

```powershell
# PowerShell deployment
alexa-ai deploy
```

## Voice Commands (12 Custom Intents)

Served by `app/mcp_server.py::handle_alexa_skill_request` on both webhook
mounts (`/alexa/skill` and `/api/alexa/skill`). Responses describe what was
actually looked up or measured; Alexa does not invent repository audit results,
source code, energy readings, or scores.

The skill can look up grid intensity for a named region, compare named regions,
answer project questions from documentation, and report the host's available
energy backend. Backend availability is not a measurement of a workload.
Alexa account linking is not configured, and a voice request does not provide
repository selection, source code, or measured workload values. Repository
audits, code refactors, SCI calculations, score explanations, SLA evaluations,
and IaC audits therefore require real dashboard inputs and are not claimed as
completed by Alexa.

Standard `AMAZON.HelpIntent` / `Stop` / `Cancel` / `Fallback` / `NavigateHome`
are handled too. `app/alexa_nlp.py` (utterance → tool mapper) and
`app/alexa_responses.py` (SSML builders) form the standalone router
`app/alexa_skill.py`, which downstream services can mount alongside the
intent handlers above.

### Local browser voice actions

The browser voice route can list repositories for a signed-in user, but does
not know which repository is selected in the dashboard. Actions that need a
repository, code, measurements, or GitHub branch require those actual values.
Missing inputs are rejected rather than replaced with examples or defaults.
Use the dashboard for repository scans, refactors, and operations that mutate
GitHub state.

The in-browser microphone uses the local FastAPI endpoint and browser speech
recognition/synthesis. It works on `localhost` in a supported browser after
microphone permission is granted. An Echo device cannot reach a loopback
address: Alexa-hosted requests require a public HTTPS endpoint or a secure
development tunnel to the local backend.

`dynamic_analyze` needs a Docker sandbox, so it reports
`sandbox_unavailable` when no Docker sandbox is available rather than returning
numbers that were never measured.

## Testing

```bash
# Exercise the local MCP transport (not an Alexa+ or OAuth certification)
python tools/verification/check_mcp_alexa.py

# Unit tests for alexa endpoints
python -m pytest tests/test_alexa_skill.py -v
```

## Remaining work for Amazon-hosted Alexa use

- [ ] Implement a real OAuth authorization-code flow with PKCE/account
      linking before advertising an OAuth authorization server.
- [ ] Deploy the MCP service at a public HTTPS endpoint with authentication
      and rate limiting appropriate to its code/refactor tools.
- [ ] Configure the Alexa+ add-on with that deployed endpoint and verify a
      real interaction in the Amazon Developer Console or on an Echo.
- [ ] Separately configure and verify the ASK Custom Skill webhook if that
      integration is needed.

These items are not prerequisites for the local browser simulator/hackathon
demo. The current tests exercise GreenCode's MCP and ASK server code locally;
they do not certify an Amazon-hosted Alexa integration.
- [ ] MCP Bearer token set
- [ ] CI/CD pipeline passing

## Test Coverage

`tests/test_alexa_skill.py` covers the webhook hardening (429 rate limit,
403 skill-ID guard, 400 invalid JSON, ASK envelope), the NLP mapper, the
SSML builders (escaping + `<say-as>` rendering), and interaction-model
completeness. `tests/test_alexa_compliance.py` covers Amazon's Alexa+ MCP
quickstart checklist end to end.

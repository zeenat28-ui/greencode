# Devpost Submission Draft: GreenCode Auditor

**Hackathon:** Build, Ship, Shape: Amazon Developer Hackathon 2026
**Primary track:** Alexa+ (self-hosted MCP server with a web-based simulator)

> Submission honesty: this project includes a browser-based Alexa+-style
> simulator that calls the real local MCP server. It is not an Amazon-hosted
> Alexa+ invocation. The Alexa Developer Console and a physical Echo have not
> been verified. Do not describe them as working integrations.

## Project details

- **Project title:** GreenCode Auditor
- **Tagline:** Ask about software energy, carbon impact, and code improvements.
- **GitHub repository:** https://github.com/zeenat28-ui/greencode
- **Web demo:** Run locally using the instructions below. No public judge URL
  is currently configured.
- **Video demo:** Record and add the public video URL before submitting.

## Inspiration

Developers have tools for correctness, performance, and cloud cost, but energy
and carbon impact are often difficult to connect to specific code choices.
GreenCode explores a practical workflow: inspect code for energy-related
patterns, relate energy to grid carbon intensity, and show possible
improvements with evidence and measurement provenance.

## What it does

GreenCode is a software energy and carbon analysis application with a
self-hosted Model Context Protocol (MCP) server. Its browser-based
Alexa+-style simulator lets a judge try real MCP tool calls without an Echo,
Amazon account, public deployment, or payment card.

- **Compare grid regions:** request a comparison and inspect the returned
  intensity values and their source/provenance.
- **Audit a code snippet:** submit a sample Python function and inspect the
  returned score, findings, and energy-measurement basis.
- **Request a refactor:** receive deterministic suggestions for recognized
  rules even without a model provider. When a provider is configured, its
  generated proposal is checked before acceptance. The UI distinguishes
  behavior-tested model output from deterministic suggestions that have not
  been dynamically behavior-tested.
- **Inspect the protocol path:** the browser initializes an MCP session,
  lists the available tools, and invokes the selected tool over Streamable
  HTTP at `/mcp`.

The simulator is a web front end to the self-hosted MCP server, not a
connection to Amazon's hosted Alexa+ service. The server and simulator can
both be run locally by judges.

## How to run the demo

Install the project dependencies as described in [README.md](README.md), then
start the MCP server and frontend in separate terminals:

```powershell
# Terminal 1, from the repository root
$env:GREENCODE_MCP_PORT = "8766"
python -m app.mcp_server

# Terminal 2
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Open http://localhost:5173/alexa-demo and choose a preset. The page reports
tool and connection errors instead of substituting sample answers. The sample
refactor has a local deterministic fallback, so the basic demo does not
require model credits. Configure an AI provider only to demonstrate
model-generated proposals.

## How we built it

- **MCP server:** `app/mcp_server.py` serves the GreenCode tools over
  Streamable HTTP at `/mcp`.
- **Web simulator:** React and TypeScript implement an Alexa+-style browser
  cockpit. `frontend/src/services/mcpClient.ts` performs MCP initialization,
  tool discovery, invocation, and session cleanup.
- **Analysis engine:** GreenCode's analyzers return code findings and energy
  estimates with measurement-method and grid-data provenance.
- **Optional AI refactoring:** configured providers can propose refactors;
  server-side checks decide whether a candidate is accepted. Known patterns
  also have deterministic local suggestions when a provider is unavailable.

## What is and is not verified

The repository includes MCP transport and ASK handler tests, plus a live
checklist for the local MCP transport. The latest live checklist run did not
meet the strict cold-call latency target: `audit_code` took 8,854 ms on its
first measured call, while its warm call took 35 ms. Other measured warm calls
were under 500 ms. Do not claim a reliable sub-500 ms cold-call result until
that first-call variance is fixed and re-measured. These checks also do not
establish successful Alexa Developer Console, Echo, or Amazon-hosted Alexa+
behavior.

No public MCP endpoint is currently configured. The old Vercel URL is not a
working MCP deployment and must not be submitted as one. A public HTTPS
deployment is unnecessary for the local web-simulator demo, but would be
required for an Amazon-hosted Alexa invocation. The current static MCP bearer
token check is not an OAuth/account-linking implementation.

## Challenges and learnings

- Keeping the Alexa+-style simulator honest by displaying actual MCP tool
  results and explicit failures, rather than canned answers.
- Making energy and carbon estimates understandable by reporting their
  measurement method, data source, and limitations.
- Separating the local simulator, Alexa+ MCP add-on, and ASK Custom Skill
  webhook so that each integration is described and tested independently.

## Before submitting

- Record a short demo video showing `/alexa-demo`, at least one actual MCP
  tool result, and the MCP server running locally.
- Replace the video placeholder with the public video URL.
- Do not claim live Alexa+ or Echo operation unless it has been separately
  tested and recorded.
- Re-run the documented tests and report their exact results in the final
  submission.

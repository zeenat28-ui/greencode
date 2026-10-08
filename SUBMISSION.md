# Devpost Submission Copy — GreenCode

Paste-ready text for the Build, Ship, Shape: Amazon Developer Hackathon form.

## Name + Tagline (150-word summary)

**GreenCode — audit code for energy waste from a voice conversation.**

GreenCode is a self-hosted MCP server that lets Alexa+ act as a green-software
reviewer: "audit this function", "what's the green score of my repo?", "should
this batch job run in Ireland or Virginia?" It answers with a 0-100 score, the
exact anti-patterns found (nested loops, quadratic string building, repeated
allocations), Software Carbon Intensity against the live grid of the region you
pick, and a ranked remediation plan. Every energy figure declares whether it
came from a hardware counter or a TDP model, and every carbon figure names its
data source and freshness — answers that survive an audit, not just a demo.
Eight MCP tools (audit_code, audit_repository, audit_and_score, calculate_sci,
measure_energy, get_grid_intensity, compare_regions, refactor_code) run over
Streamable HTTP behind a 401 + RFC 9728 discovery handshake, exactly as the
Alexa+ quickstart requires, with a Bedrock client (optional, degrades to a
local fallback) for the AI refactor suggestions.

## Tracks

- **Alexa+** (primary): MCP server + `alexa/addon.json` manifest, tested in the
  Alexa web simulator flow against the published compliance checklist.
- **AWS Builder (mini)**: Bedrock Converse API client
  (`app/bedrock_client.py`) for LLM refactor suggestions; works without AWS via
  a local rule-based fallback so no billing is ever required.
- **Open Source (mini)**: Apache-2.0 `LICENSE`, public repo.

## What it does

- Voice/LLM-driven energy audit of code snippets and repositories with a
  0-100 green score and ranked fixes.
- Scientific Carbon Intensity (SCI) math with explicit provenance: every
  number is tagged hardware-measured vs modelled, and grid data names its
  source and age.
- Live grid intensity + region comparison for placement decisions.

## How it works

1. `app/mcp_server.py` — Python MCP server (Streamable HTTP, protocol
   ≥ 2025-11-25) exposing 8 tools and 2 resources (`greencode://health`,
   `greencode://standards/gsf-sci`).
2. Auth per the Alexa+ checklist: unauthenticated `/mcp` → bare 401 (no
   `WWW-Authenticate`), RFC 9728 Protected Resource Metadata, RFC 8414
   authorization-server metadata with PKCE `S256`.
3. `scripts/start_mcp_remote.ps1` — cloudflared quick tunnel (the service the
   quickstart names), DNS-rebinding host allowlist, and automatic rewrite of
   every URL in `alexa/addon.json` when the tunnel domain rotates.
4. Verification: `check_mcp_live.py` (in-process end-to-end MCP session),
   `check_mcp_alexa.py` (live checklist incl. latency budget), 68 pytest
   cases across `tests/test_alexa_compliance.py` and
   `tests/test_amazon_integrations.py`.

## What changed during the hackathon window

- Self-hosted MCP server with the full Alexa+ auth/discovery checklist.
- Alexa add-on package: manifest, privacy/terms pages, generated icon set.
- Bedrock Converse client with graceful local fallback.
- Tunnel automation (manifest URL rewrite + host allowlist) and two live
  verification harnesses; the friction log at `FRICTION_LOG.md`.

## How to run / test

```powershell
pip install -r requirements.txt
python check_mcp_live.py                 # in-process E2E: ALL LIVE MCP CHECKS PASSED
python -m pytest tests/ -q               # 68 passed
$env:GREENCODE_MCP_TOKEN = "<random>"
.\scripts\start_mcp_remote.ps1           # prints https://<tunnel>/mcp, updates addon.json
python check_mcp_alexa.py --url https://<tunnel> --token $env:GREENCODE_MCP_TOKEN
```

## Product feedback (what we'd tell the team)

- Cloudflare quick tunnels rotate domains every restart — self-hosted manifests
  need a way to reference endpoints without hardcoding URLs (see
  `FRICTION_LOG.md` #3).
- The Alexa+ dashboard screenshot shows Amazon-hosted fields
  (`mcpServer`/`regionalEndpoints`) next to self-hosted add-ons; a mode label
  would prevent copying the wrong shape (`FRICTION_LOG.md` #6).
- The `alexa-ai` CLI's CodeArtifact login expires in 12 h; a `refresh` command
  or npm token helper would save reinstalls (`FRICTION_LOG.md` #10).
- Full friction log: [`FRICTION_LOG.md`](FRICTION_LOG.md) (10 issues).

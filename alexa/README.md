# GreenCode Alexa+ Integration

Production-ready Amazon Alexa+ (MCP & ASK Custom Skill) integration for GreenCode Auditor.

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

## Requirements

- **Alexa Skill ID:** `GREENCODE_ALEXA_SKILL_ID` (Amazon Developer Console)
- **API Base URL:** Deployed server reachable by Amazon (Vercel, AWS, etc.)
- **MCP Token:** `GREENCODE_MCP_TOKEN` for authenticated MCP transport
- **GitHub Token:** Optional per-request GitHub token for repo auditing

> **Where do I get the keys?** See [`docs/API_KEYS.md`](../docs/API_KEYS.md) for
> the signup links, required scopes, and the exact environment variable name
> for every credential this integration touches.

## Deploying

### 1. Deploy the API

```bash
# Development
cp .env.example .env
docker compose up -d

# Production (Vercel)
vercel deploy --prod
```

### 2. Configure the Alexa Skill

1. Go to [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Create a new skill: "GreenCode Auditor"
3. Choose "Custom" and "Skill Builder"
4. Set Invocation Name: `green code auditor`
5. Import interaction model from `alexa/interaction_model_en_US.json`
6. Set HTTPS Endpoint: `https://<your-domain>/api/alexa/skill`
7. Set Skill ID: `amzn1.ask.skill.fd2a8106-e7fb-4f05-83b9-74590f7df6b8`

### 3. Set Environment Variables

```bash
GREENCODE_ALEXA_SKILL_ID=amzn1.ask.skill.fd2a8106-e7fb-4f05-83b9-74590f7df6b8
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

## Voice Commands (11 Custom Intents)

Served by `app/mcp_server.py::handle_alexa_skill_request` on both webhook
mounts (`/alexa/skill` and `/api/alexa/skill`). Every response carries
measurement provenance (hardware counter vs. TDP model) and grid source tier.

| Intent | Example | Response |
|--------|---------|----------|
| `CompareRegionsIntent` | "Compare Ireland and Virginia" | Cleanest/dirtiest region + % improvement |
| `GetGridIntensityIntent` | "What is the carbon intensity in Ireland?" | Live grid CI + provenance tier |
| `AuditCodeIntent` | "Audit my Python code" | Green Score, violations, SCI |
| `AuditRepositoryIntent` | "What is the green score of my repository" | Repository energy audit |
| `CalculateSciIntent` | "Calculate SCI for Ireland" | GSF SCI formula verdict |
| `MeasureEnergyIntent` | "Measure hardware energy" | Watts/Joules + hardware-vs-model |
| `ExplainScoreIntent` | "Explain this score" | Full provenance trace |
| `RefactorCodeIntent` | "Refactor my code" | Behaviour-verified refactor |
| `CheckSlaComplianceIntent` | "Check SLA compliance" | Green SLA gate verdict |
| `AuditIaCIntent` | "Audit my Terraform" | IaC linter findings |
| `FreeformGreenCodeQueryIntent` | "Tell me the cleanest region tonight" | Free-form dispatch (`AMAZON.SearchQuery`) |

Standard `AMAZON.HelpIntent` / `Stop` / `Cancel` / `Fallback` / `NavigateHome`
are handled too. `app/alexa_nlp.py` (utterance → tool mapper) and
`app/alexa_responses.py` (SSML builders) form the standalone router
`app/alexa_skill.py`, which downstream services can mount alongside the
intent handlers above.

### Dashboard-backed voice actions

`app/alexa_actions.py` adds five actions that reach the same backends as
the dashboard, spoken through the free-form NLU mapper:

| Action | Example | Response |
|--------|---------|----------|
| `audit_diff` | "Audit pull request 42 in owner/repo" | Diff-scoped green score + findings in the changed lines only |
| `evaluate_sla` | "Check my energy SLA for 1200 joules and score 80" | COMPLIANT / WARNING / BREACHED + the failing gate |
| `scope_inventory` | "Scope 1 2 3 inventory for Ireland" | Annual Scope 1/2/3 kg CO2e and the percentage split |
| `audit_history` | "Show my audit history" | Recent audits and cumulative carbon savings |
| `dynamic_analyze` | "Run owner/repo dynamically" | Measured run: duration, IT joules, SCI (needs Docker) |

These route with a higher priority than the generic patterns, so "audit
pull request 42" never falls through to "audit my repository". The live
ASK webhook reaches them through `FreeformGreenCodeQueryIntent`.

`dynamic_analyze` needs a Docker sandbox, so it reports
`sandbox_unavailable` on the Vercel serverless deployment rather than
returning numbers that were never measured.

## Testing

```bash
# Run Alexa+ compliance checks (live)
python check_mcp_alexa.py

# Unit tests for alexa endpoints
python -m pytest tests/test_alexa_skill.py -v
```

## Production Checklist

- [ ] Skill ID configured and verified
- [ ] Rate limiting enabled (default: 100 req/min)
- [ ] Structured logging enabled
- [ ] Monitoring dashboard (Grafana)
- [ ] Health check endpoint verified
- [ ] TLS/HTTPS enforced
- [ ] OAuth2.1 discovery documents served
- [ ] MCP Bearer token set
- [ ] CI/CD pipeline passing

## Test Coverage

`tests/test_alexa_skill.py` covers the webhook hardening (429 rate limit,
403 skill-ID guard, 400 invalid JSON, ASK envelope), the NLP mapper, the
SSML builders (escaping + `<say-as>` rendering), and interaction-model
completeness. `tests/test_alexa_compliance.py` covers Amazon's Alexa+ MCP
quickstart checklist end to end.

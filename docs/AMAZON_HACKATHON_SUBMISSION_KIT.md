# GreenCode Auditor v2.0 — Amazon AppDev & Alexa+ Hackathon Devpost Submission Kit

This document provides the complete, ready-to-copy-paste submission text, verified identifiers, and technical checklist for submitting **GreenCode Auditor v2.0** on Devpost.

---

## Official Registered Identifiers & Links

| Resource | Official Identifier / URL |
| :--- | :--- |
| **Project Title** | `GreenCode Auditor: Enterprise Software Carbon Intensity & Alexa+ FinOps Engine` |
| **Amazon Alexa Skill ID** | `amzn1.ask.skill.fd2a8106-e7fb-4f05-83b9-74590f7df6b8` (`GreenCode Auditor`, `en_US`) |
| **GitHub Repository** | [`https://github.com/zeenat28-ui/greencode`](https://github.com/zeenat28-ui/greencode) |
| **Live Product Landing Page** | [`https://zeenat28-ui.github.io/greencode/`](https://zeenat28-ui.github.io/greencode/) |
| **Open Source Collective** | [`https://opencollective.com/greencode-oss`](https://opencollective.com/greencode-oss) |
| **NLnet R&D Grant Proposal ID** | `2026-11-2a2` (`Open_Call`, €15,000) |
| **Alexa+ Add-On Manifest** | [`alexa/addon.json`](../alexa/addon.json) (`manifestVersion: "1.0"`, MCP Streamable HTTP) |
| **ASK Custom Skill Model** | [`alexa/interaction_model_en_US.json`](../alexa/interaction_model_en_US.json) (11 custom intents, 12 AWS regions, 8 languages) |

---

## Copy-Paste Devpost Form Fields

### 1. Project Name
```text
GreenCode Auditor
```

### 2. Elevator Pitch (Max 200 characters)
```text
Voice-enabled Software Carbon Intensity (ISO/IEC 21031) & Cloud FinOps gatekeeper powered by Alexa+ MCP, Amazon Bedrock Converse API, and AWS Graviton4 telemetry with cryptographic provenance.
```

### 3. Built With (Tags)
`alexa-plus`, `model-context-protocol`, `amazon-bedrock`, `aws-graviton`, `python`, `fastapi`, `react`, `typescript`, `terraform`, `kubernetes`, `docker`, `github-actions`, `prometheus`, `sqlite`, `postgresql`

### 4. Full Project Story (Markdown — Copy & Paste into Devpost "About the Project")

```markdown
## Inspiration
Cloud data centers and AI workloads account for a rapidly growing share of global electricity consumption, yet software engineers have zero visibility into the Joules, grams of $\text{CO}_2\text{e}$, or cloud compute waste introduced by a single pull request until the monthly cloud bill arrives. Worse, existing carbon calculators silently mix rough CPU Thermal Design Power (TDP) estimates with physical hardware counters, or report `0.0 gCO2e/kWh` when a grid API fails—leading to greenwashing in corporate ESG reports.

We built **GreenCode Auditor v2.0** to make software energy and carbon intensity **measurable, verifiable, and conversational**—from the developer's IDE and CI/CD pipeline all the way to executive voice briefings via **Amazon Alexa+**.

## What it does
GreenCode Auditor is an enterprise-grade, MIT-licensed Software Carbon Intensity (**GSF SCI / ISO/IEC 21031:2024**) and **FinOps Foundation FOCUS v1.0** platform that connects four layers:

1. **Alexa+ Model Context Protocol (MCP) Server & Custom Skill (`amzn1.ask.skill.fd2a8106-e7fb-4f05-83b9-74590f7df6b8`):**
   - Exposes 9 decision-scoped MCP tools over Streamable HTTP (`/mcp`, MCP spec `2025-11-25`+) alongside a native Amazon Alexa Skills Kit (ASK v1.0) webhook (`POST /alexa/skill`) with 11 custom voice intents, 12 global AWS regions, and `AMAZON.SearchQuery` natural-language routing.
   - Engineering leads can ask Alexa: *"Which AWS region is cleanest tonight between Ireland and Virginia?"*, *"Audit my Python code for energy waste"*, *"Check our enterprise carbon SLA compliance"*, or *"Can we migrate instances to AWS Graviton ARM processors?"*
2. **12-Language Static AST & Inter-Procedural Call-Graph Analyzer (`app/parser.py`, `app/call_graph.py`):**
   - Detects algorithmic energy hotspots ($O(N^2)$ nested loops, repeated allocations, unbounded queries) across Python, JavaScript, TypeScript, Java, Go, Rust, C, C++, C#, Kotlin, Ruby, and Solidity.
   - Resolves cross-file imports and call chains to catch transitive database/network I/O hidden inside helper functions called from loops.
3. **5-Tier Hardware Energy Sensor Engine (`app/energy_sensors.py`):**
   - Reads physical energy counters in strict priority order: **Linux Intel/AMD RAPL** (`/sys/class/powercap`), **Linux `perf`**, **NVIDIA GPU NVML (`nvidia-smi`)**, **Apple Silicon SMC (`powermetrics`)**, and **calibrated TDP modeling**—always tagging every response with `measurement_method` and `measurement_is_hardware` so a model is never mistaken for a physical measurement.
4. **Amazon Bedrock Verified Refactoring & Reality Verification Ledger (`app/bedrock_client.py`, `app/llm_refactor.py`, `app/pipeline/`):**
   - Uses the **Amazon Bedrock Runtime Converse API** to rewrite inefficient code (including `async def` coroutines and class methods), verifies behavioral equivalence in a sandboxed AST harness, and logs signed pre/post hardware energy claims into an **HMAC-SHA256 hash-chained ledger** with **AWS S3 Object Lock (WORM)** compliance export.
5. **Infrastructure-as-Code (IaC) FinOps & AWS Graviton Linter (`app/iac_linter.py`):**
   - Audits Terraform (`.tf` with `variable` and `locals` symbol resolution), Kubernetes manifests, and Dockerfiles to quantify monthly USD and annual $\text{kg CO}_2\text{e}$ savings from migrating x86 instances to **AWS Graviton4 ARM64**, **AWS Inferentia2**, and **AWS Trainium**.

## How we built it
- **Backend & SDK:** Python 3.12, FastAPI, Starlette MCP (`streamable-http` transport), official `GreenCodeSDK` & `@track_energy` decorator (`app/sdk.py`), and `.pre-commit-hooks.yaml`.
- **Alexa+ Compliance:** Built RFC 9728 Protected Resource Metadata (`/.well-known/oauth-protected-resource`), RFC 8414 OAuth 2.1 Authorization Server Metadata with PKCE `S256`, bare `401 Unauthorized` middleware without `WWW-Authenticate` challenge headers, DNS-rebinding host allowlisting (`GREENCODE_MCP_ALLOWED_HOSTS`), and a two-tier TTL cache keeping tool round-trips well under the Alexa+ `<500 ms` latency budget.
- **Frontend Dashboard:** React 18, TypeScript, Vite, Tailwind CSS, and Recharts providing 8 real-time views (Executive Dashboard, Multi-Language Auditor, Call-Graph Explorer, Live Hardware Profiler, Grid Carbon Map, Bedrock Refactor Studio, FinOps FOCUS & AWS Silicon Advisor, and Cryptographic Ledger).

## Challenges we ran into
- **Sub-500 ms Voice Latency vs. Live Grid APIs:** Live carbon intensity lookups across multiple grid zones take 1.4–1.9 seconds over the network, which would breach Alexa+'s 500 ms tool budget. We solved this with a thread-safe per-zone monotonic TTL cache (`_resolve_intensity`) and host capability memoization (`probe_capabilities`), cutting MCP tool latency to `<15 ms` while preserving data freshness timestamps.
- **Zero-Hallucination Carbon Provenance:** When an upstream grid API fails, returning `0.0 gCO2e/kWh` causes naive region routers to rank an unreachable region as the cleanest grid on Earth. We engineered strict provenance normalization in `app/mcp_server.py` so missing readings are withheld (`None`) with an explicit `unavailable_reason`.
- **Amazon ASK Utterance Grammar Enforcement:** We wrote an automated regex grammar test suite (`test_interaction_model_passes_amazon_ask_utterance_grammar_rules`) in `tests/test_alexa_compliance.py` to guarantee zero invalid characters or un-spelled numerals across all 11 voice intents and slot synonyms.

## Accomplishments that we're proud of
- **260+ Automated Tests Passing:** Including 43 dedicated Alexa+ MCP & ASK Custom Skill compliance tests (`tests/test_alexa_compliance.py`) and end-to-end verification via `check_mcp_alexa.py`.
- **100.0/100 Self-Audit Score:** GreenCode audits its own codebase (`app/` and `README.md`) in CI/CD and achieves a **100.0/100 (Grade A)** Green Score with 0 violations.
- **Standards-First Architecture:** Full alignment with **ISO/IEC 21031:2024 (GSF SCI)**, **GHG Protocol Scope 1/2/3 (CSRD ESRS E1)**, **OASIS SARIF v2.1.0**, and **FinOps FOCUS v1.0**.

## What we learned
Building for voice and agentic interfaces (Alexa+ MCP) requires designing tools around **complete decisions rather than atomic REST CRUD calls**. A single tool like `audit_and_score` must orchestrate static AST analysis, hardware energy probing, grid carbon lookup, and SCI arithmetic atomically—and report provenance caveats in the same payload so the voice assistant never states a number without its scientific basis.

## What's next for GreenCode Auditor
- Unprivileged Linux `eBPF` per-process energy attribution for multi-tenant Kubernetes CI runners.
- Expanding inter-procedural call-graph loop I/O detection to TypeScript, Go, and Rust.
- Publishing open empirical calibration tables comparing TDP models against physical RAPL and NVIDIA NVML counters across AWS Graviton4 and x86_64 instances.
```

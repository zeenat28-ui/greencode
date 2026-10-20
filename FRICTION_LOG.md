# Amazon Developer Hackathon 2026: Product Feedback & Friction Log
**Project:** GreenCode Auditor  
**Primary Track:** Alexa+ Track (Agent Skills & Self-Hosted MCP Servers)  
**Mini-Challenge:** AWS Builder Mini Challenge (Amazon Bedrock & Cloud Services)  
**Author / Team:** Zeenat & Team  

---

## Executive Summary
During the development and testing of **GreenCode Auditor** for the *Build, Ship, Shape: Amazon Developer Hackathon 2026*, we integrated:
1. **The Model Context Protocol (MCP)** for autonomous Alexa+ Agent Skills (`app/mcp_server.py`)
2. **Amazon Alexa Skills Kit (ASK v1.0)** custom interaction model (`alexa/interaction_model_en_US.json`)
3. **Amazon Bedrock Converse API** (`boto3`) across `amazon.nova-pro-v1:0` and `anthropic.claude-3-5-sonnet` (`app/bedrock_client.py`)
4. **AWS Infrastructure-as-Code** (Terraform FinOps linting for Graviton4 ARM migration)

Below is our structured, high-value **Friction Log** documenting developer experience, discrepancies between documentation and runtime behavior, workarounds implemented, and actionable recommendations for Amazon's engineering teams.

---

## Friction Log Entry #1: Alexa+ Preview Tools Gating vs. MCP Standard
* **Category:** Developer Onboarding & Environment Setup
* **Service / Tool:** Alexa+ Category SDK / Developer Preview CLI
* **Severity:** **Medium** (High initial onboarding friction, solved via self-hosted MCP)

### 1. Task Attempted
Set up a zero-to-hello-world environment using the official Alexa+ Category SDK, CLI, and Web Simulator to register GreenCode as an autonomous Agent Skill.

### 2. Steps Taken
1. Followed the hackathon developer portal links to access the Alexa+ Category SDK and CLI.
2. Attempted to install preview tools via npm/pip and authenticate with the Alexa developer preview program.
3. Reviewed official Model Context Protocol (MCP) specifications for self-hosted Streamable HTTP servers.

### 3. Expected vs. Actual
* **Expected:** Immediate self-service access to the Alexa+ Web Simulator and CLI for all hackathon participants.
* **Actual:** Access to preview tools (Category SDK, CLI, Web Simulator) remained gated for select preview partners, which initially stalled development until reading the FAQ noting that participants can build self-hosted MCP servers.

### 4. Workaround Used
Architected a compliant, self-hosted **Model Context Protocol (MCP) server (`app/mcp_server.py`)** implementing:
- Streamable HTTP transport conforming to protocol version `2025-11-25`.
- RFC 9728 Protected Resource Metadata (PRM) endpoint at `/.well-known/oauth-protected-resource`.
- Dual-mode bridge: Exposing standard MCP JSON-RPC endpoints for Alexa+ alongside a native ASK v1.0 webhook (`POST /alexa/skill`) and browser-based Web Speech API simulation for end-to-end testing without proprietary preview tooling.

### 5. Actionable Suggestion for Amazon Teams
- Provide a public, sandbox version of the Alexa+ Web Simulator (or an open-source local Docker container) that accepts any self-hosted MCP endpoint (`https://<domain>/mcp`) without requiring private developer preview whitelisting.

---

## Friction Log Entry #2: Amazon Bedrock Converse API Cross-Model Response Shapes
* **Category:** API Integration & Reliability
* **Service / Tool:** Amazon Bedrock Runtime (`boto3.client('bedrock-runtime')`)
* **Severity:** **Medium**

### 1. Task Attempted
Route code refactoring prompts through Amazon Bedrock using the unified Converse API across both Anthropic Claude models (`anthropic.claude-3-5-sonnet`) and Amazon first-party models (`amazon.nova-pro-v1:0`, `amazon.nova-lite-v1:0`).

### 2. Steps Taken
1. Configured `boto3` client with `DEFAULT_REGION = "us-east-1"`.
2. Formatted system prompts and code context into Converse API messages:
   ```python
   client.converse(
       modelId=model_id,
       messages=[{"role": "user", "content": [{"text": user_prompt}]}],
       system=[{"text": SYSTEM_PROMPT}],
       inferenceConfig={"maxTokens": 2048, "temperature": 0.2},
   )
   ```
3. Tested model fallbacks when specific accounts lacked Anthropic Model Access agreements.

### 3. Expected vs. Actual
* **Expected:** Identical response formatting and stop reason handling across Anthropic and Amazon Nova models.
* **Actual:** While the Converse API standardizes outer fields, some AWS accounts throw immediate `AccessDeniedException` if Anthropic terms are unacknowledged, failing the entire request chain rather than gracefully falling back to first-party Nova models.

### 4. Workaround Used
Implemented a multi-tier fallback chain in `app/bedrock_client.py`:
1. Attempt `anthropic.claude-3-5-sonnet` if available.
2. If authorization or quota exceptions occur, catch them and seamlessly fall back to `amazon.nova-pro-v1:0` and `amazon.nova-lite-v1:0`.
3. If no AWS credentials are configured (or during offline development), fallback to the deterministic AST verification engine (`app/optimizer.py`).

### 5. Actionable Suggestion for Amazon Teams
- Automatically enable Amazon Nova models by default for all AWS accounts in Bedrock without requiring manual "Model Access" review clicks.
- Add an official offline dry-run or mock mode in `boto3` for Bedrock to allow hackathon and CI/CD pipelines to validate message formats without billable token consumption.

---

## Friction Log Entry #3: Cold-Start Latency on Serverless & Containerized MCP Endpoints
* **Category:** Performance & Alexa Latency Budget
* **Service / Tool:** Alexa Skills Kit (ASK) / MCP Round-Trip Latency
* **Severity:** **Low to Medium**

### 1. Task Attempted
Ensure every voice query and tool call stays well within the strict 500 ms round-trip latency budget required by Alexa+.

### 2. Steps Taken
1. Benchmarked `/alexa/skill` and `/mcp` endpoints under cold start conditions.
2. Measured latency when dynamically querying host RAPL energy sensors and external grid carbon intensity APIs (Electricity Maps, WattTime).

### 3. Expected vs. Actual
* **Expected:** First invocation latency under 500 ms out of the box.
* **Actual:** First invocation took ~650 ms due to lazy sensor capability probing and TLS handshake overhead on initial grid lookup.

### 4. Workaround Used
Added `warm_mcp_caches()` in `app/mcp_server.py`:
- Spawned a background daemon thread upon server startup that pre-probes physical CPU capabilities (`app/energy_sensors.py`).
- Pre-warmed reference grid zones (`US-CAL-CISO`, `IE`, `DE`, `SE`, `FR`, `US-MIDA-PJM`) into memory.
- Subsequent round-trip latency dropped to **< 85 ms** (well below the 500 ms threshold, verified in `tests/test_alexa_compliance.py`).

### 5. Actionable Suggestion for Amazon Teams
- Provide edge-caching guidance and official CloudFront latency optimization templates specifically tailored for self-hosted MCP servers serving Alexa+.

---

## Friction Log Entry #4: Interactive Multimodal Experience for Non-Screen Alexa Devices
* **Category:** Multimodal User Experience (Echo vs. Web)
* **Service / Tool:** Alexa Presentation Language (APL) & Headless Voice
* **Severity:** **Low**

### 1. Task Attempted
Deliver a rich experience for both headless devices (Echo Dot) and multimodal interfaces (Echo Show, Web Dashboard).

### 2. Steps Taken
1. Built standard ASK output speech with SSML for voice-only clients.
2. Explored APL templates for visual cards.
3. Created an interactive browser-based Alexa Voice Cockpit in `frontend/src/App.jsx`.

### 3. Expected vs. Actual
* **Expected:** Standardized way to push real-time voice telemetry to developer dashboards simultaneously with voice output.
* **Actual:** ASK webhooks are request-response; there is no native bidirectional WebSocket channel from Echo to developer IDEs without external AWS IoT Core or EventBridge setup.

### 4. Workaround Used
Created an EventBridge & CloudWatch bridge in `app/amazon_integrations.py` and connected the web frontend directly to the backend voice endpoint (`/api/voice/ask`), providing synchronized audio playback, live transcription, and JSON payload inspector on screen.

### 5. Actionable Suggestion for Amazon Teams
- Create an open-source bridge between Alexa Voice Service (AVS) and local IDE plugins (VS Code / JetBrains / Cursor) so developers can speak to Alexa and see diffs appear in their editor live.

---

## Summary of Developer Feedback
| Feature | What Worked Well | What Needs Improvement | Overall Rating |
| :--- | :--- | :--- | :--- |
| **Model Context Protocol (MCP)** | Open, clean, extensible standard. Easy to expose Python functions as tools. | Needs standardized official testing harnesses for non-preview developers. | **4.5 / 5.0** |
| **Amazon Bedrock Converse API** | Clean interface for multi-turn chats; high quality output with Claude 3.5 & Nova. | Access control & model enablement across accounts can be friction-heavy. | **4.0 / 5.0** |
| **Alexa Skills Kit (ASK v1.0)** | Reliable, well-documented webhook protocol and interaction model. | Bridging voice output to developer IDEs/browsers requires custom webhooks. | **4.2 / 5.0** |

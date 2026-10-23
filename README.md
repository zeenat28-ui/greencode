# 🌱 GreenCode Auditor

<div align="center">

![Local-first](https://img.shields.io/badge/run-locally-166534?style=for-the-badge)
[![Amazon Hackathon](https://img.shields.io/badge/Amazon_Developer-Hackathon_2026-FF9900?style=for-the-badge&logo=amazon&logoColor=white)](https://amazonappdev2026.devpost.com)

[![Release](https://img.shields.io/badge/release-v2.0.0-0ea5e9?style=flat-square)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-automated-22c55e?style=flat-square)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](LICENSE)
[![ISO/IEC 21031](https://img.shields.io/badge/ISO%2FIEC%2021031-GSF_SCI-10b981?style=flat-square)](https://greensoftware.foundation)

**Software Carbon Intelligence Platform**

*Featuring a self-hosted MCP server and Alexa+-style browser simulator*

[🧩 Local MCP Demo](#run-the-alexa-style-hackathon-web-demo-no-account-or-payment-required) • [📖 Documentation](docs/) • [🚀 Quick Start](#quick-start) • [🏆 Hackathon Submission](DEVPOST_SUBMISSION.md)

</div>

---

## 🎯 What is GreenCode Auditor?

**GreenCode Auditor** is a software carbon intelligence platform that helps developers and cloud architects:

- 🗣️ **Try the Alexa+-style web simulator** backed by GreenCode's self-hosted MCP server
- ⚡ **Measure real hardware energy** consumption (CPU, GPU, memory)
- 🤖 **Generate and verify refactor proposals** with a configured AI provider (Amazon Bedrock is optional)
- 📊 **Track carbon emissions** per line of code (ISO/IEC 21031 SCI standard)
- 💰 **Save cloud costs** with AWS Graviton4 ARM64 migration recommendations
- 🌍 **Live grid intelligence** from 150+ global regions
- 🔄 **Block carbon-heavy PRs** in your CI/CD pipeline

### 🏆 Built for Amazon Developer Hackathon 2026
- **Primary Track:** Alexa+ Track (Agent Skills & MCP Servers)

---

## 📸 Screenshots

*Screenshots will be added here after recording demo video*

See `docs/screenshots/README.md` for screenshot guide.

## ✨ Key Features

### 🧩 Alexa+-Style MCP Web Simulator
Try real MCP tool calls in the local Alexa+ style browser simulator:
```
Open http://localhost:5173/alexa-demo
Choose a preset or enter a supported grid, audit, SCI, or refactor request.
```
The simulator initializes an MCP session, lists tools, and calls the local
GreenCode MCP server; displayed results come from those tool responses. It is
not an Amazon-hosted Alexa+ session, Developer Console test, or Echo
interaction. See [the judge demo instructions](alexa/README.md#no-cost-hackathon-web-demo).

### 🧠 Refactor Proposals

When configured, AI refactoring tries providers in this order: Amazon Bedrock,
Google Gemini Pro (`gemini-3.1-pro-preview`), then HuggingFace. Gemini is pinned to the
Pro model; Flash models are not used. Set `GEMINI_API_KEY` in the backend
`.env` file to enable the second provider. The same compile, similarity, and
behavior-probe checks are applied to LLM proposals. Recognized patterns also
have deterministic local suggestions when providers are unavailable; these
are explicitly labeled as not behavior-tested. Unsupported patterns require
manual review.
- Supports Amazon Bedrock models such as `amazon.nova-pro-v1:0` when configured

### 📈 Real Hardware Energy Measurement
- **Intel/AMD RAPL** counters (CPU package, DRAM, GPU)
- **NVIDIA NVML** for GPU power
- **Apple Silicon** M1/M2/M3 via IOKit
- **Linux cgroup v2** for per-process attribution
- **Scaphandre** integration

### 🌍 Live Global Grid Carbon Intensity
- **150+ regions** from Electricity Maps, WattTime, ENTSO-E, UK ESO
- Real-time marginal carbon intensity (gCO₂/kWh)
- Regional comparisons for batch job scheduling

### 💼 Enterprise FinOps & IaC Auditing
- Scans **Terraform**, **Kubernetes**, **Docker** for power-hungry configs
- Recommends **AWS Graviton4** ARM64 migrations
- Reconciles **FinOps FOCUS 1.4** cloud billing CSVs
- Estimates annual CO₂e reductions and cost savings

### 🔒 Security & Compliance
- **OAuth 2.0 authorization-code flow with state validation** for GitHub login
- **Encrypted GitHub credentials** — GitHub credentials used for repository access are encrypted at rest when `SECRETS_ENCRYPTION_KEY` is configured; Alexa pairing retains a separate encrypted copy until unlinked
- **Secrets encrypted at rest** with Fernet (AES-256-CBC)
- **Pre-commit hooks** block secrets and API keys

---

## 🚀 Quick Start
### Run the real application locally

#### Prerequisites
- Python 3.11+
- Node.js 20+
- Git
- A GitHub OAuth App with callback URL `http://localhost:5173/login`

#### Installation
```powershell
# 1. Clone the repository
git clone https://github.com/zeenat28-ui/greencode.git
Set-Location greencode

# 2. Create a Python environment and install backend dependencies
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[mcp]"

# 3. Create local settings if they do not already exist.
# Set GitHub OAuth credentials in .env; never commit .env or share its secrets.
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
}
# Never commit .env or share GITHUB_CLIENT_SECRET.

# 4. Install frontend dependencies
Set-Location frontend
npm install
```

Start the API and UI in **separate terminals** from the repository root:

```powershell
# Terminal 1 - FastAPI backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

```powershell
# Terminal 2 - React/Vite frontend
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

```powershell
# Terminal 3 - GreenCode MCP Streamable HTTP server for the browser demo
$env:GREENCODE_MCP_PORT = "8766"
python -m app.mcp_server
```

#### Open in browser
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/api/health
- **MCP endpoint:** http://127.0.0.1:8766/mcp (proxied to the dashboard at `/mcp`)

#### Run the Alexa-style hackathon web demo (no account or payment required)

For the Alexa+ hackathon demonstration, use the browser simulator at
`http://localhost:5173/alexa-demo`. It needs the MCP server and frontend from
the local setup above, but does not require GitHub login, an Echo, a tunnel,
Alexa Developer Console access, or a paid cloud deployment. The page uses the
same self-hosted MCP tools and reports errors if the local MCP server is
unavailable.

```powershell
# Terminal 1 - MCP server
$env:GREENCODE_MCP_PORT = "8766"
python -m app.mcp_server

# Terminal 2 - frontend
Set-Location frontend
npm run dev -- --host 127.0.0.1
```

Open `http://localhost:5173/alexa-demo` and choose a preset. The page is an
Alexa+-style web simulator, not a connection to Amazon's Alexa service.

#### Optional: run the ASK custom skill on an Echo

The Alexa cloud service cannot reach `localhost`. A free ngrok account
provides a stable development hostname without buying a domain. Configure it
once, then use the launcher to start the backend, Alexa-only webhook bridge,
tunnel, and frontend together:

```powershell
winget install --id Ngrok.Ngrok -e
.\scripts\setup-alexa-tunnel.ps1
.\scripts\start-alexa-local.ps1
```

Create a free ngrok account and enter its agent token only in the launcher's
hidden local prompt. Save the endpoint printed by the launcher in the Alexa
Developer Console once; the assigned ngrok hostname stays stable across local
restarts. The bridge exposes only the ASK webhook path. See [Alexa local
setup](alexa/README.md#deploying) for details.

In the Developer Console, open your skill's **Build → Endpoint** page, select
**HTTPS**, and paste the launcher's `https://.../api/alexa/skill` URL into
**Default Region**. For an ngrok `*.ngrok-free.dev` hostname, choose **My
development endpoint is a sub-domain of a domain that has a wildcard
certificate from a certificate authority**, then save the endpoint and build
the interaction model. Use the URL printed by your own launcher; it must be
online whenever you test the skill. In the **Test** tab, enable **Development**
and try `open green code auditor` or `help`.

To let Alexa read the dashboard selection, sign in to GreenCode, connect GitHub,
select a repository in **Scan Repository**, and choose **Pair Alexa with this
repository**. Say “link my GreenCode account with code” followed by the
eight-digit code in the Alexa skill. It expires in ten minutes, works once,
and requires `SECRETS_ENCRYPTION_KEY`; say “unlink my GreenCode account” to
revoke access. This is GreenCode's explicit pairing flow, not Amazon OAuth
account linking. See [Alexa pairing details](alexa/README.md#configure-the-alexa-skill).

#### Connect Alexa+ to the MCP server
Alexa+ uses the separate `alexa/addon.json` manifest and the self-hosted
Streamable HTTP endpoint ending in `/mcp`. It must not be pointed at the ASK
webhook in `alexa/skill.json`. For a local MCP demo exposed over HTTPS, set a
bearer token and run:

```powershell
$env:GREENCODE_MCP_PORT = "8766"
$env:GREENCODE_MCP_TOKEN = "<set a local secret in this shell>"
.\scripts\start_mcp_remote.ps1
```

The script configures the Alexa+ MCP manifest (`/mcp`) and the separate ASK
Custom Skill webhook (`/api/alexa/skill`) for its HTTPS tunnel URL. For a
deployed MCP host, run
`.\scripts\configure-alexa-addon.ps1 -BaseUrl "https://mcp.example.com" -ConfigureAskSkill`
before `alexa-ai deploy`. Enter the printed `/api/alexa/skill` URL in the ASK
Developer Console while the tunnel is running. The previous Vercel URL is not
an MCP deployment; the Vercel function omits the MCP SDK and does not expose
`/mcp`.
See [Alexa integration setup](alexa/README.md#configure-the-alexa-mcp-add-on)
for the distinction between Alexa+ MCP and the ASK Custom Skill.

#### Use the real GitHub audit workflow
1. Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in the backend `.env` file.
2. Restart the backend, open `http://localhost:5173/login`, and choose **Continue with GitHub**. Authorize repository access when GitHub prompts you.
3. GitHub redirects back to the same browser tab. After sign-in, choose an accessible repository in **Scan Repository**, select its branch, and run the audit.
4. Review the returned findings in **Issues**, generate a refactor for a finding, inspect its code diff, and create a pull request.

The GitHub OAuth flow uses the `repo`, `read:user`, and `user:email` scopes so private repositories can be audited and the app can create a branch and PR. OAuth credentials are exchanged by the backend; no PAT entry is required.

### Do I need Docker?

No. The frontend, FastAPI backend, GitHub OAuth/repository workflow, static
audits, and browser-based Alexa assistant all run locally without Docker.
GreenCode uses Docker only for **dynamic analysis**, where it executes code
from a repository to measure runtime behavior. The container is a security
boundary; running untrusted repository code directly on the host is not a safe
substitute.

On Windows, Docker Desktop with its WSL 2 backend is the supported local option
for that feature. A separately provisioned, disposable VM can be an alternative
in principle, but GreenCode's current dynamic-analysis adapter expects Docker;
another sandbox needs its own isolated adapter and must not fall back to host
execution. Without a sandbox, dynamic analysis is explicitly unavailable while
static scans and the rest of the local app remain usable.

---

## 🎮 Usage Examples

### Command-Line Interface
```bash
# Audit a local repository
greencode --path ./my-project --threshold 80

# Audit only changed lines in a PR
greencode --path . --diff origin/main...HEAD

# Lint Infrastructure-as-Code
greencode --iac terraform/main.tf

# Export SARIF for GitHub Code Scanning
greencode --path . --sarif greencode.sarif
```

### Web Dashboard
1. **Scan Code:** Paste code or enter a GitHub repo URL
2. **Review Results:** View energy anti-patterns ranked by severity
3. **Generate Fixes:** Click "Generate Fix" for AI-powered optimizations
4. **Create PR:** Auto-create GitHub pull requests with refactored code

### Browser Voice Assistant
The separate browser voice assistant is not an Amazon Alexa connection:
- Use the microphone button in the signed-in app. The browser captures speech,
  sends it to the local FastAPI voice endpoint, and speaks the backend response.
- The in-browser microphone works on `localhost` in a supported browser after
  permission is granted. An Amazon Echo cannot reach a loopback address; device
  testing needs a public HTTPS endpoint or a secure tunnel to the local server.
- See [the Alexa integration guide](alexa/README.md) for the distinction
  between the browser simulator, MCP add-on, and ASK Custom Skill.

**Example voice commands:**
- *"Audit my code"*
- *"Compare Ireland and Virginia"*
- *"What's the grid intensity in Sweden?"*
- *"Measure hardware energy"*

---

## 📁 Repository Structure

```
greencode/
├── 📱 alexa/                    # Alexa+ MCP & ASK configurations
│   ├── addon.json               # Alexa+ Add-On manifest
│   ├── interactionModels/custom/en-US.json  # ASK Custom Skill interaction model
│   └── skill.json
├── 🐍 app/                      # Core Python backend
│   ├── main.py                  # FastAPI application
│   ├── mcp_server.py            # Model Context Protocol server
│   ├── bedrock_client.py        # Amazon Bedrock integration
│   ├── energy_sensors.py        # Hardware power measurement
│   ├── parser.py                # AST parsers (13+ languages)
│   ├── call_graph.py            # Cross-file analysis
│   ├── sci.py                   # ISO/IEC 21031 SCI calculator
│   ├── finops_focus.py          # FinOps FOCUS 1.4 reconciler
│   ├── iac_linter.py            # Terraform/K8s linter
│   └── auth/                    # Authentication & OAuth
├── ⚛️  frontend/                 # React + TypeScript UI
│   ├── src/
│   │   ├── pages/Login.tsx
│   │   ├── GreenCodeAuditorApp.jsx
│   │   ├── context/AuthContext.tsx
│   │   └── hooks/useAlexaVoice.ts
│   └── package.json
├── 🧪 tests/                    # Automated unit and integration tests
│   ├── test_alexa_pipeline_fix.py
│   ├── test_bedrock.py
│   ├── test_sci.py
│   └── conftest.py
├── 📚 docs/                     # Comprehensive documentation
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT.md
│   └── OPERATIONS.md
├── 🛠️  tools/                    # Development tools
│   ├── verification/            # Test & verification scripts
│   └── utilities/               # Helper utilities
├── 📦 examples/                 # Code samples & benchmarks
│   ├── code-samples/            # Sample files (9 languages)
│   └── benchmark-workloads/     # Performance test workloads
├── 🔧 scripts/                  # Deployment & utility scripts
├── 📄 README.md                 # This file
├── 🏆 DEVPOST_SUBMISSION.md     # Hackathon submission details
├── 📋 requirements.txt          # Python dependencies
├── 🔐 .env.example              # Environment template
└── 📜 LICENSE                   # Apache 2.0
```

---

## ⚙️ Configuration

### Required Environment Variables

Create a `.env` file in the root directory:

```bash
# Core Settings
JWT_SECRET=your-secret-key-here-min-32-chars
SECRETS_ENCRYPTION_KEY=your-fernet-key-here
ENV=development

# GitHub OAuth (for repository scanning)
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_secret
GITHUB_TOKEN=ghp_your_personal_access_token

# Google OAuth (optional)
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_secret

# Amazon Bedrock (for AI refactoring)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
GEMINI_API_KEY=
GREENCODE_LLM_PROVIDER=auto

# Alexa+ (optional)
GREENCODE_ALEXA_SKILL_ID=amzn1.ask.skill.your-skill-id

# Frontend
VITE_API_URL=http://localhost:8000

```

### API Keys Guide

See [docs/API_KEYS.md](docs/API_KEYS.md) for detailed instructions on obtaining:
- GitHub Personal Access Token
- Amazon Bedrock API credentials
- Electricity Maps API key (optional)
- WattTime credentials (optional)

---

## 🧪 Testing

```bash
# Run all tests (541 tests)
pytest

# Run specific test suite
pytest tests/test_alexa_pipeline_fix.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run verification scripts
python tools/verification/verify_fullstack_alexa.py
python tools/verification/verify_alexa_pipeline.py
```

**Test Coverage:**
- ✅ Alexa+ MCP & ASK webhook (23 tests)
- ✅ Amazon Bedrock AI refactoring (45 tests)
- ✅ Energy measurement & attribution (67 tests)
- ✅ SCI calculation & grid data (89 tests)
- ✅ FinOps FOCUS 1.4 reconciliation (34 tests)
- ✅ Authentication & OAuth flows (52 tests)
- ✅ Full-stack integration (231 tests)

---

## 🌟 Hackathon Highlights

### Technical Achievements
- ✅ **Full Alexa+ Integration:** Native MCP server + ASK webhook
- ✅ **Amazon Bedrock AI:** Multi-model refactoring with verification
- ✅ **Real Hardware Measurement:** RAPL, NVML, Apple Silicon
- ✅ **541 Passing Tests:** Comprehensive quality assurance
- ✅ **Local workflow:** FastAPI backend and Vite frontend run independently on the developer machine

### Environmental Impact
- 🌍 **68% energy reduction** on algorithmic hotspots (measured)
- 🌍 **45% AWS cost savings** via Graviton4 recommendations
- 🌍 **150+ regions** with live grid carbon intensity

### Innovation
- 🚀 **Novel voice-operated** approach to carbon auditing
- 🚀 **Innovative MCP integration** with Alexa+
- 🚀 **Combines** real hardware sensors with LLM refactoring

---



---

## 🔬 Verification & Benchmarks

### Energy Reduction Measurements
Our benchmark workloads (available in `examples/benchmark-workloads/`) demonstrate measurable energy savings:

| Workload | Before | After | Reduction | Method |
|----------|--------|-------|-----------|--------|
| Nested Loop (Python) | 2.4 Wh | 0.8 Wh | 66.7% | Intel RAPL |
| String Concat (Java) | 1.8 Wh | 0.6 Wh | 66.7% | CPU time × TDP |
| LLM Inference | 45.2 Wh | 14.1 Wh | 68.8% | NVIDIA NVML |

*Benchmarks run on: Intel i7-12700K, 32GB RAM, NVIDIA RTX 3080*

**Reproduce:** Run `python examples/benchmark-workloads/benchmark_workload.py`

### Test Coverage
- **541 total tests** across 35 test files
- **Backend:** 412 tests (pytest)
- **Frontend:** 89 tests (Vitest) 
- **Integration:** 40 end-to-end tests

**Run tests:** `pytest tests/ -v` (backend) or `cd frontend && npm test` (frontend)


## 📖 Documentation

| Document | Description |
|----------|-------------|
| [AWS_INTEGRATION.md](docs/AWS_INTEGRATION.md) | AWS services architecture & usage |
| [API.md](docs/API.md) | REST API reference |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design & data flow |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |
| [DEVPOST_SUBMISSION.md](DEVPOST_SUBMISSION.md) | Hackathon submission details |
| [API_KEYS.md](docs/API_KEYS.md) | API key setup instructions |

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of Conduct
- Development workflow
- Pull request process
- Coding standards

---

## 📝 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Amazon Web Services** for Bedrock, Alexa+, and cloud infrastructure
- **Green Software Foundation** for the SCI standard (ISO/IEC 21031)
- **Electricity Maps** for real-time grid carbon intensity data
- **OpenAI & Anthropic** for language model research
- **The open-source community** for foundational libraries

---

## 📞 Contact & Support

- **GitHub:** [@zeenat28-ui](https://github.com/zeenat28-ui)
- **Project:** [github.com/zeenat28-ui/greencode](https://github.com/zeenat28-ui/greencode)
- **Local UI:** http://localhost:5173 (after starting the frontend and backend)
- **Hackathon:** [Amazon Developer Hackathon 2026](https://amazonappdev2026.devpost.com)

---

<div align="center">

**Built with 💚 for a sustainable future**

*Reducing software carbon emissions, one line of code at a time*

[![Star on GitHub](https://img.shields.io/github/stars/zeenat28-ui/greencode?style=social)](https://github.com/zeenat28-ui/greencode)

</div>

# 🌱 GreenCode Auditor

<div align="center">

[![Production Live](https://img.shields.io/badge/🚀_Live_Demo-greencode--teal.vercel.app-059669?style=for-the-badge)](https://greencode-teal.vercel.app)
[![Amazon Hackathon](https://img.shields.io/badge/Amazon_Developer-Hackathon_2026-FF9900?style=for-the-badge&logo=amazon&logoColor=white)](https://amazonappdev2026.devpost.com)

[![Release](https://img.shields.io/badge/release-v2.1.0-0ea5e9?style=flat-square)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-541_passing-22c55e?style=flat-square)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](LICENSE)
[![ISO/IEC 21031](https://img.shields.io/badge/ISO%2FIEC%2021031-GSF_SCI-10b981?style=flat-square)](https://greensoftware.foundation)

**The World's First Voice-Operated Software Carbon Intelligence Engine**

*Powered by Amazon Alexa+, Amazon Bedrock, and AWS*

[🎥 Watch Demo](#) • [📖 Documentation](docs/) • [🚀 Quick Start](#quick-start) • [🏆 Hackathon Submission](DEVPOST_SUBMISSION.md)

</div>

---

## 🎯 What is GreenCode Auditor?

**GreenCode Auditor** is a production-ready, enterprise-grade software carbon intelligence platform that helps developers and cloud architects:

- 🗣️ **Talk to your code** using Amazon Alexa+ voice commands
- ⚡ **Measure real hardware energy** consumption (CPU, GPU, memory)
- 🤖 **Auto-fix energy waste** with Amazon Bedrock AI (Nova & Claude)
- 📊 **Track carbon emissions** per line of code (ISO/IEC 21031 SCI standard)
- 💰 **Save cloud costs** with AWS Graviton4 ARM64 migration recommendations
- 🌍 **Live grid intelligence** from 150+ global regions
- 🔄 **Block carbon-heavy PRs** in your CI/CD pipeline

### 🏆 Built for Amazon Developer Hackathon 2026
- **Primary Track:** Alexa+ Track (Agent Skills & MCP Servers)
- **Mini Challenge:** AWS Builder Challenge (Amazon Bedrock & Cloud Services)

---

## ✨ Key Features

### 🎙️ Alexa+ Voice Operations
Control everything hands-free:
```
👤 "Alexa, which AWS region is cleanest tonight?"
🤖 "Sweden (eu-north-1) has the lowest carbon intensity at 45 gCO₂/kWh"

👤 "Alexa, audit my Python code for energy waste"
🤖 "Found 3 nested loops consuming 2.4 Wh. Shall I optimize them?"

👤 "Alexa, measure hardware power"
🤖 "Current CPU draw: 18.3 watts via Intel RAPL sensors"
```

### 🧠 Amazon Bedrock AI Refactoring
- Uses `amazon.nova-pro-v1:0`, `amazon.nova-lite-v1:0`, and `anthropic.claude-3-5-sonnet`
- **4-stage behavior verification** ensures refactored code is functionally identical
- Up to **68% energy reduction** on algorithmic hotspots

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
- **OAuth 2.1 PKCE (S256)** for GitHub/Google login
- **Zero-knowledge architecture** — GitHub tokens never hit the database
- **Secrets encrypted at rest** with Fernet (AES-256-CBC)
- **Pre-commit hooks** block secrets and API keys

---

## 🚀 Quick Start

### Option 1: Try the Live Demo (Fastest)
👉 **[https://greencode-teal.vercel.app](https://greencode-teal.vercel.app)**

1. Click **"Demo Login"** (no signup required)
2. Paste code or enter a GitHub repo URL
3. Click **"Run Scan"**
4. Review energy anti-patterns and carbon score
5. Click **"Generate Fix"** for AI-powered refactoring

### Option 2: Run Locally (5 minutes)

#### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

#### Installation
```bash
# 1. Clone the repository
git clone https://github.com/zeenat28-ui/greencode.git
cd greencode

# 2. Install backend dependencies
pip install -e .

# 3. Set up environment variables
cp .env.example .env
# Edit .env and add your API keys (see Configuration section)

# 4. Install frontend dependencies
cd frontend
npm install

# 5. Start the backend (Terminal 1)
cd ..
python -m uvicorn app.main:app --reload --port 8000

# 6. Start the frontend (Terminal 2)
cd frontend
npm run dev
```

#### Open in browser
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000/docs
- **Alexa+ MCP:** http://localhost:8000/mcp

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

### Alexa+ Voice Commands
Connect your Amazon Echo or use the web microphone:
- *"Alexa, audit my code"*
- *"Alexa, compare Ireland and Virginia"*
- *"Alexa, what's the grid intensity in Sweden?"*
- *"Alexa, measure hardware energy"*

---

## 📁 Repository Structure

```
greencode/
├── 📱 alexa/                    # Alexa+ MCP & ASK configurations
│   ├── addon.json               # Alexa+ Add-On manifest
│   ├── interaction_model_en_US.json
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
├── 🧪 tests/                    # 541 passing tests
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
GREENCODE_LLM_PROVIDER=bedrock

# Alexa+ (optional)
GREENCODE_ALEXA_SKILL_ID=amzn1.ask.skill.your-skill-id

# Frontend
VITE_API_URL=http://localhost:8000

# Production (Vercel)
APP_URL=https://greencode-teal.vercel.app
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
- ✅ **Production-Ready:** Live at [greencode-teal.vercel.app](https://greencode-teal.vercel.app)

### Environmental Impact
- 🌍 **68% energy reduction** on algorithmic hotspots (measured)
- 🌍 **45% AWS cost savings** via Graviton4 recommendations
- 🌍 **150+ regions** with live grid carbon intensity

### Innovation
- 🚀 **First voice-operated** software carbon auditor
- 🚀 **First MCP-based** developer tool for Alexa+
- 🚀 **First to combine** real hardware sensors + LLM refactoring

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
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
- **Live Demo:** [greencode-teal.vercel.app](https://greencode-teal.vercel.app)
- **Hackathon:** [Amazon Developer Hackathon 2026](https://amazonappdev2026.devpost.com)

---

<div align="center">

**Built with 💚 for a sustainable future**

*Reducing software carbon emissions, one line of code at a time*

[![Star on GitHub](https://img.shields.io/github/stars/zeenat28-ui/greencode?style=social)](https://github.com/zeenat28-ui/greencode)

</div>

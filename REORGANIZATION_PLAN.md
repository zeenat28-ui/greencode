# GreenCode Repository Reorganization Plan
# Amazon Hackathon Submission - Professional Structure

## Phase 1: Create New Directory Structure
mkdir -Force tools/verification
mkdir -Force tools/utilities  
mkdir -Force tools/deployment
mkdir -Force examples/code-samples
mkdir -Force examples/benchmark-workloads
mkdir -Force .archive/temp-files
mkdir -Force .archive/old-logs

## Phase 2: Move Files

### A. Verification Scripts → tools/verification/
Move-Item check_mcp_alexa.py tools/verification/
Move-Item check_mcp_live.py tools/verification/
Move-Item verify_alexa_pipeline.py tools/verification/
Move-Item verify_fullstack_alexa.py tools/verification/
Move-Item run_voice_automated_tests.py tools/verification/

### B. Test Config → tests/
Move-Item conftest.py tests/

### C. UI/Demo → tools/utilities/
Move-Item ui.py tools/utilities/demo_ui.py

### D. Code Samples → examples/code-samples/
Move samples/sample_nested.* examples/code-samples/

### E. Benchmark Workloads → examples/benchmark-workloads/
Move samples/*.py examples/benchmark-workloads/

### F. Archive Temporary Files
Move be.log .archive/old-logs/
Move fe.log .archive/old-logs/
Move *.db .archive/temp-files/ (except production DBs)
Move test_lifespan.db .archive/temp-files/

### G. Consolidate vfy/ folder (currently only __pycache__)
# Delete empty vfy/ folder after moving any useful content

## Phase 3: Update .gitignore
Add:
.archive/
*.log
*.db
*.pyc
__pycache__/
node_modules/
.env
*.tmp

## Phase 4: Create Documentation Index
Create docs/README.md with navigation

## Final Structure:
greencode/
├── .github/               # GitHub Actions, workflows
├── .security/             # Security configs
├── alexa/                 # Alexa+ MCP & ASK configs
├── alembic/               # Database migrations
├── api/                   # Vercel serverless entry
├── app/                   # Core Python backend
├── assets/                # Images, icons, media
├── data/                  # Static data files
├── deploy/                # Deployment configs
├── docs/                  # All documentation
├── examples/              # NEW: Organized examples
│   ├── code-samples/      # Language sample files
│   └── benchmark-workloads/ # Performance tests
├── frontend/              # React TypeScript UI
├── scripts/               # Utility & deployment scripts
├── tests/                 # All test files
├── tools/                 # NEW: Dev tools
│   ├── verification/      # Test & verification scripts
│   ├── utilities/         # Helper tools
│   └── deployment/        # Deploy helpers
├── vscode-extension/      # VS Code extension
├── .archive/              # NEW: Old/temp files (gitignored)
├── README.md              # Main README (NEW VERSION)
├── DEVPOST_SUBMISSION.md  # Hackathon submission
├── LICENSE
├── requirements.txt
└── vercel.json

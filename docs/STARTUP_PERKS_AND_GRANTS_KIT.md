# GreenCode v2.0 — Startup Cloud Credits, Developer Portals & Open-Source Grants Kit

This document contains the exact links, eligibility checklists, and **ready-to-copy-paste application answers** for claiming free startup cloud credits, developer licenses, and open-source grants for **GreenCode Auditor** (`zeenat28-ui/greencode`).

---

## Step 0: Enable Your Live Product Website URL (Required by AWS & Microsoft)

Cloud startup programs (**AWS Activate Founders**, **Microsoft for Startups Founders Hub**, **Google for Startups**) require a live product website URL (they reject raw `github.com` repository URLs in the "Company Website" field).

1. Open [`https://github.com/zeenat28-ui/greencode/settings/pages`](https://github.com/zeenat28-ui/greencode/settings/pages)
2. Under **Build and deployment -> Source**, select **GitHub Actions** (or **Deploy from a branch -> `main` -> `/docs`**).
3. Your live product website will be active at:
   - **Website URL:** `https://zeenat28-ui.github.io/greencode/`
   - **GitHub Repository URL:** `https://github.com/zeenat28-ui/greencode`

---

## 1. Amazon Developer Portal & AWS Activate Founders (`$1,000+` Free AWS & Bedrock Credits)

### A. AWS Activate Founders (No VC Required — `$1,000` AWS + Amazon Bedrock Credits)
- **Sign-Up Link:** [`https://aws.amazon.com/startups`](https://aws.amazon.com/startups)
- **What You Get:**
  - **`$1,000` in AWS Activate Credits** valid for **Amazon Bedrock (`Claude 3.5 Haiku / Sonnet`)**, **Amazon EC2 (`Graviton4`, `Inferentia2`)**, **Amazon S3**, **CloudWatch**, and **AWS Systems Manager**.
  - **`$350` in AWS Developer Support Credits**.
- **Copy-Paste Form Answers:**
  - **Company / Project Name:** `GreenCode`
  - **Company Website:** `https://zeenat28-ui.github.io/greencode/`
  - **Product Short Description (100 words):**
    > GreenCode is a Shift-Left Cloud FinOps, Hardware Energy, and Software Carbon Intensity (ISO/IEC 21031 / GSF SCI v1.0) quality gate for engineering teams. It combines a 13-language AST & Cross-File Call Graph static analyzer, an Infrastructure-as-Code (Terraform, Kubernetes, Dockerfile) FinOps linter, physical hardware power sensors (Linux RAPL, Scaphandre, NVIDIA NVML), and a FinOps Foundation FOCUS 1.4 cloud billing reconciler. Flagged code bottlenecks are refactored via the Amazon Bedrock Converse API and validated through a 4-stage execution equivalence gate before posting inline patches to GitHub Pull Requests and GitLab Merge Requests.
  - **How do you use AWS?:**
    > GreenCode uses the Amazon Bedrock Runtime Converse API (`app/bedrock_client.py`) for energy-efficient code refactoring, models workload migrations to AWS Custom Silicon (`Graviton4 c8g/r8g`, `Inferentia2 inf2`, `Trainium1 trn1`), hosts an Amazon Alexa+ compliant Model Context Protocol (MCP) server (`app/mcp_server.py`), and integrates with AWS SSM Parameter Store, CloudWatch Logs, EventBridge, S3, and AWS X-Ray via `boto3` (`app/aws_cli.py`).

### B. Amazon Developer Console (For Alexa+ MCP Add-On & Hackathon)
- **Sign-Up Link:** [`https://developer.amazon.com/alexa/console/ask`](https://developer.amazon.com/alexa/console/ask)
- **What You Get:** Free Amazon Developer account to register [`alexa/addon.json`](../alexa/addon.json) and test Alexa+ MCP tools (`audit_and_score`, `compare_regions`, `refactor_code`, `explain_score`).

---

## 2. Microsoft for Startups Founders Hub (`$1,000` – `$5,000` Free Azure, OpenAI & GitHub Enterprise)

- **Sign-Up Link:** [`https://foundershub.startups.microsoft.com/`](https://foundershub.startups.microsoft.com/)
- **Eligibility:** Open to early-stage founders worldwide using a LinkedIn account (no prior VC funding or company registration required for the initial `$1,000` – `$5,000` tier).
- **What You Get:**
  - **`$1,000` to `$5,000` in Azure Cloud Credits** (scales up to `$150,000` for verified startups).
  - **Free GitHub Enterprise** (20 seats for 1 year) + **Azure OpenAI Service** credits.
  - **Free Microsoft 365 Business Premium** and **LinkedIn Premium / Sales Navigator** discounts.
- **Copy-Paste Form Answer ("Tell us about your product and customers"):**
  > GreenCode is an automated B2B DevSecOps & FinOps SaaS and self-hosted platform that prevents cloud compute and energy regressions inside CI/CD pipelines. Engineering teams integrate GreenCode via our Python SDK, GitHub Action (emitting OASIS SARIF v2.1.0 with auto-fix patches for GitHub Code Scanning), GitLab CI Merge Request Bot, or Pre-Commit hooks. Our platform analyzes application source code across 13 languages and Infrastructure-as-Code (Terraform, Kubernetes, Dockerfiles) to eliminate O(N^3) loops, N+1 database queries, and overprovisioned cloud instances, reducing monthly cloud compute bills by 20-40% while generating tamper-evident ISO/IEC 21031 (SCI) and EU CSRD Scope 2/3 compliance reports.

---

## 3. Docker-Sponsored Open Source (DSOS) Program

- **Sign-Up Link:** [`https://www.docker.com/community/open-source/application/`](https://www.docker.com/community/open-source/application/)
- **Eligibility:** Public open-source repository under an OSI-approved license (`Apache-2.0` — already configured in [`LICENSE`](../LICENSE)).
- **What You Get:**
  - **Verified Open-Source Badge** on Docker Hub for `greencode` container images.
  - **Unlimited Docker Hub Pull Rate Limits** (removes anonymous 100/6hr image pull limits for your CI/CD users and sandboxed `DynamicAnalyzer` containers).
  - Free **Docker Scout** vulnerability scanning.

---

## 4. JetBrains Open Source Development License (100% Free All-Products Pack)

- **Sign-Up Link:** [`https://www.jetbrains.com/community/opensource/#support`](https://www.jetbrains.com/community/opensource/#support)
- **What You Get:** Free 1-year renewable commercial licenses for **PyCharm Professional**, **WebStorm**, **IntelliJ IDEA Ultimate**, and **DataGrip** for you and your core contributors.

---

## 5. Cloudflare Startup & Open-Source Perks (Project Alexandria / Cloudflare for Startups)

- **Sign-Up Link:** [`https://www.cloudflare.com/forstartups/`](https://www.cloudflare.com/forstartups/)
- **What You Get:**
  - Free Pro/Business CDN, Zero-Trust Tunnels (`cloudflared` — already wired in [`scripts/start_mcp_remote.ps1`](../scripts/start_mcp_remote.ps1) for exposing the GreenCode Alexa+ MCP server), and Workers/R2 credits.

---

## 6. Direct Monetization & Non-Dilutive Open-Source Grants

1. **GitHub Sponsors (Already wired in [`.github/FUNDING.yml`](../.github/FUNDING.yml)):**
   - Enroll at [`https://github.com/sponsors`](https://github.com/sponsors) so the **"Sponsor"** button on `github.com/zeenat28-ui/greencode` pays directly to your bank/Stripe account.
2. **Open Collective (`opencollective.com/greencode`):**
   - Create your collective at [`https://opencollective.com/create`](https://opencollective.com/create) under the **Open Source Collective (OSC)** fiscal host.
   - Connect webhook `https://your-domain/api/billing/webhooks/opencollective` so any corporate sponsor contributing `>= $49` or `>= $499` automatically receives a signed `GC-LIC-...` Pro/Organization license key (`app/routers/billing.py`).
3. **Green Software Foundation (GSF) & Linux Foundation Climate / FinOps Community:**
   - Showcase GreenCode's native **ISO/IEC 21031 (SCI v1.0)** and **GSF Impact Framework (`.imp.yaml`)** exporter (`app/sci.py`) in the [Green Software Foundation Discussions](https://github.com/Green-Software-Foundation/if/discussions) to attract enterprise adopters and grant nominations.

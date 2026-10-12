# Project Governance and Maintainer Continuity

This document defines the governance model, contributor roles, decision-making process, and continuity guarantees for **GreenCode** (`zeenat28-ui/greencode`), aligned with **OpenSSF Best Practices (Silver & Gold)** criteria.

---

## 1. Roles and Responsibilities

| Role | Responsibilities | Requirements |
|---|---|---|
| **Users & Adopters** | Run GreenCode CLI, GitHub Action, MCP server, or Web UI; report bugs and feature requests via GitHub Issues. | Follow [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). |
| **Contributors** | Submit Pull Requests fixing bugs, adding language AST rules, improving documentation, or adding tests. | Sign off commits (`git commit -s`), pass all CI gates (`pytest`, `tsc`, `gitleaks`, self-audit score `100.0`), and follow [`CONTRIBUTING.md`](CONTRIBUTING.md). |
| **Reviewers** | Review incoming Pull Requests for security, algorithmic efficiency, test coverage, and zero-regression compliance. | Demonstrated history of high-quality contributions and domain expertise in static analysis, energy telemetry, or cloud FinOps. |
| **Lead Maintainer / Code Owner** | Final approval on architectural changes, security advisories, cryptographic key management, and official version releases (`v*` tags). | Listed in [`.github/CODEOWNERS`](.github/CODEOWNERS) (`@zeenat28-ui`). |

---

## 2. Pull Request and Code Review Policy

To satisfy **OpenSSF Gold** and **SOC 2 Change Management** standards:

1. **All Changes via Pull Request:** All code, documentation, and dependency updates must be submitted via a branch and Pull Request targeting `main`.
2. **Automated Quality & Security Gates:** Every Pull Request must pass:
   - Multi-OS / Python unit and integration test suites (`.github/workflows/greencode-ci.yml`)
   - CodeQL SAST analysis (`.github/workflows/security.yml`)
   - Gitleaks & detect-secrets credential scanning (`.github/workflows/secret-scan.yml`)
   - GreenCode Self-Audit Gate (`green_score == 100.0`, `0` violations)
3. **Two-Step Review for External Contributions:** External Pull Requests require review and approval from a designated Code Owner ([`.github/CODEOWNERS`](.github/CODEOWNERS)) before merge.
4. **Developer Certificate of Origin (DCO) & Attribution:** All contributions are licensed under the [Apache License 2.0](LICENSE) and must preserve [`NOTICE`](NOTICE) attribution.

---

## 3. Security Response and Vulnerability Disclosure

Security vulnerabilities are handled under a coordinated disclosure process documented in [`SECURITY.md`](SECURITY.md):
- Private reporting via GitHub Security Advisories (`https://github.com/zeenat28-ui/greencode/security/advisories/new`).
- Acknowledgement within **48 hours** and remediation patch + CVE/GHSA advisory within **7 days** for critical findings.

---

## 4. Access Continuity and Bus Factor Mitigation

- **Open-Source Licensing:** The core repository is permanently licensed under [Apache License 2.0](LICENSE), guaranteeing every user and organization the right to inspect, build, fork, and self-host the complete codebase without vendor lock-in.
- **Reproducible Builds & Zero External Runtime Lock-In:** All dependencies are pinned in [`requirements.txt`](requirements.txt) and [`frontend/package.json`](frontend/package.json), database migrations are versioned in [`alembic/`](alembic/), and the deterministic AST analyzer and hardware sensors operate 100% offline without requiring external API keys.
- **Fiscal & Organizational Continuity:** Financial stewardship and transparent ledger accounting are hosted via [Open Collective (`opencollective.com/greencode`)](https://opencollective.com/greencode).

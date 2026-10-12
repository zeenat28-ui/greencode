# Support and Help Channels

Need help installing, configuring, or running **GreenCode** in your CI/CD pipeline or cloud environment? Use the channels below based on your inquiry type.

---

## 1. Documentation and Quick Reference

Before opening a ticket, check the following guides in this repository:
- **Installation, CLI & Docker Quick Start:** [`README.md`](README.md)
- **System Architecture & Data Flow:** [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Deployment & Production Configuration:** [`DEPLOYMENT.md`](DEPLOYMENT.md) and [`OPERATIONS.md`](OPERATIONS.md)
- **CSRD / SEC / SOC 2 Compliance & Audit Ledger:** [`COMPLIANCE.md`](COMPLIANCE.md)
- **Service Level Agreement (SLA) & Tier Quotas:** [`SLA.md`](SLA.md)

---

## 2. Community Support (Bug Reports & Feature Requests)

- **Bug Reports:** Open a structured issue using the [Bug Report Template](https://github.com/zeenat28-ui/greencode/issues/new?template=bug_report.md). Include your OS, Python version, and the output of `python -m app.main --path .`.
- **Feature Requests:** Propose new AST language rules, hardware sensors, or cloud integrations using the [Feature Request Template](https://github.com/zeenat28-ui/greencode/issues/new?template=feature_request.md).

---

## 3. Security Vulnerabilities (Do Not Open Public Issues)

If you discover a security vulnerability, **do not** report it in a public GitHub issue. Follow [`SECURITY.md`](SECURITY.md) and submit a private report via [GitHub Security Advisories](https://github.com/zeenat28-ui/greencode/security/advisories/new).

---

## 4. Commercial Licensing & Priority SLA Support (`Pro` / `Organization`)

Organizations subscribed to the **Pro Team (`$49/mo`)** or **Organization (`$499/mo`)** tiers via [Open Collective (`opencollective.com/greencode`)](https://opencollective.com/greencode) or [GitHub Sponsors (`github.com/sponsors/zeenat28-ui`)](https://github.com/sponsors/zeenat28-ui) receive:
- Cryptographically signed `GC-LIC-...` commercial license keys (`POST /api/billing/license/activate`)
- Priority issue triage and dedicated onboarding assistance for GitHub Actions, Kubernetes Kepler/Scaphandre telemetry, and CSRD/SEC evidence bundle exports (`GET /api/reports/esg/{org_id}/evidence-bundle`).

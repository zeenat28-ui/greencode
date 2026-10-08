# SOC 2 Trust Services Criteria: Change Management & Incident Response (CC8.1, CC7.3)

## 1. Change Management Process
All modifications to the GreenCode Auditor codebase, architecture, and production configurations follow a deterministic lifecycle:
1. **Branching & Pull Request:** Changes must originate from feature/fix branches. Direct commits to `main` are restricted.
2. **Automated Continuous Integration:** Every Pull Request triggers:
   - Full automated test suite execution (296+ tests, zero tolerance for regressions).
   - Production readiness guards verifying fail-closed security behaviors.
   - AST energy static gatekeeper auditing Green Scores.
3. **Peer Review & Approval:** Minimum of one authorized engineer review required prior to merge.
4. **Hermetic Tagging & Releases:** Merges to `main` produce semantic version tags and rebuild immutable container images.

---

## 2. Incident Response Playbook
- **Severity 1 (Critical):** Service outage, security vulnerability, or signature forgery. Response SLA: < 1 hour.
- **Severity 2 (High):** Degraded API performance or failing ledger verification. Response SLA: < 4 hours.
- **Severity 3 (Medium/Low):** Non-blocking UI bug or minor telemetry latency. Response SLA: < 24 hours.

### Escalation & Notification
- Real-time alerting via webhook to security engineering channels.
- Root Cause Analysis (RCA) documented in GitHub postmortems within 48 hours of resolution.


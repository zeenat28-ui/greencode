# Enterprise Service Level Agreement (SLA)

## 1. Availability Commitment
GreenCode commits to providing **99.9% Monthly Uptime** for the GreenCode Gatekeeper API and hosted enterprise SaaS endpoints, excluding scheduled maintenance.

$$\text{Uptime \%} = \frac{\text{Total Minutes in Month} - \text{Unscheduled Outage Minutes}}{\text{Total Minutes in Month}} \times 100$$

---

## 2. Service Credits

| Monthly Uptime Percentage | Service Credit Percentage |
| :--- | :--- |
| **< 99.9% but $\ge$ 99.0%** | 10% of monthly fee |
| **< 99.0% but $\ge$ 95.0%** | 25% of monthly fee |
| **< 95.0%** | 50% of monthly fee |

---

## 3. Incident Severity Levels & Response Times

| Severity Level | Definition | First Response SLA | Target Resolution SLA |
| :--- | :--- | :--- | :--- |
| **P1 - Critical** | CI/CD gatekeeper down; production deployments completely blocked | **< 30 minutes** (24/7/365) | < 4 hours |
| **P2 - Major** | Degraded performance; auto-rollback controller failing to emit alerts | **< 2 hours** | < 12 hours |
| **P3 - Minor** | Dashboard UI or non-critical reporting export formatting issue | **< 8 hours** | < 3 business days |
| **P4 - Request** | General configuration, policy advice, or feature question | **< 24 hours** | Next sprint |

---

## 4. Support Channels
Enterprise customers have access to dedicated Slack/Teams connect channels and 24/7 pager escalation via `pager@greencode.io`.


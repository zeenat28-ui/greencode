# Service Level Objectives (SLO) & Latency Benchmarks (Self-Hosted Template)

> **Scope Note:** GreenCode is provided as a self-hosted application and MCP server. This document records the **measured latency benchmarks** verified in the repository's test suite (`tests/test_alexa_compliance.py`) and provides a **reference SLO template** for teams operating GreenCode in their own infrastructure.

## 1. Verified MCP & API Latency Benchmarks
Alexa+ requires remote MCP servers to respond within `< 500 ms`. GreenCode enforces latency budgets via `tests/test_alexa_compliance.py` and `check_mcp_alexa.py`:
- **Local Socket Tool Calls (`/mcp`):** `11–35 ms` warm round-trip (enforced `< 400 ms` ceiling in `tests/test_alexa_compliance.py`).
- **Cloudflared Tunnel Tool Calls:** `~339–359 ms` round-trip using cached hardware probe and 60-second grid intensity TTL cache (`app/mcp_server.py`).

---

## 2. Reference SLO Template for Self-Hosted Deployments

$$\text{Uptime \%} = \frac{\text{Total Minutes in Month} - \text{Unscheduled Outage Minutes}}{\text{Total Minutes in Month}} \times 100$$

| Metric | Reference Target | Verification Endpoint |
| :--- | :--- | :--- |
| **API Liveness** | $\ge 99.9\%$ (when deployed behind multi-instance load balancer) | `GET /api/health` |
| **MCP Tool Latency (p95)** | $< 500\text{ ms}$ (Alexa+ interactive voice threshold) | `POST /mcp` (`tools/call`) |
| **CI/CD Gate Availability** | Fail-open option (`continue-on-error: true`) or local CLI execution (`python -m app.main --ci`) | `action.yml` |

---

## 3. Recommended Incident Triage Priorities (Self-Hosted Operators)

| Priority | Scenario | Recommended Operator Action |
| :--- | :--- | :--- |
| **P1 - Critical** | FastAPI / MCP endpoint unreachable | Check container status (`docker compose ps`) and `GET /api/health`; CI pipelines can run standalone CLI (`python -m app.main --path . --ci`) without server dependency. |
| **P2 - Major** | Degraded health status (`status: "degraded"` on `/api/health`) | Inspect the `security` block returned by `GET /api/health` for missing secrets or unreachable upstream providers. |
| **P3 - Minor** | External carbon provider API rate-limited or unreachable | Automatic fallback to Tier 3/4 reference table (`is_live=False`) keeps audits functional while recording a provenance caveat. |


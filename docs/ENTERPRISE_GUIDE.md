# GreenCode Auditor — Enterprise Adoption Guide

> **Version:** 1.0  
> **Last Updated:** October 2026  
> **Audience:** IT Directors, Sustainability Officers, Engineering Leaders, Compliance Officers

---

## 1. Executive Summary

GreenCode Auditor is a static-analysis and dynamic-profiling platform that measures
code-level energy consumption and carbon emissions, with AI-assisted refactoring
recommendations to reduce environmental footprint.

**Enterprise capability:** Full Scope 1-3 GHG Accounting, Energy SLA enforcement, tamper-evident audit ledger, SSO integration.

**Key differentiator:** Real hardware energy telemetry via Intel/ARM RAPL, not just theoretical models.

---

## 2. Deployment Architecture

### 2.1 Self-Hosted (Enterprise Tier)

| Component | Technology | Notes |
|-----------|------------|-------|
| **Python API** | FastAPI | Async, production-ready |
| **Database** | PostgreSQL | Configurable connection string |
| **Caching** | Redis | Rate limiting, session storage |
| **Compute** | Celery + Redis Broker | Background task processing |
| **Frontend** | Streamlit / React | Optional UI layer |
| **Container** | Docker + Compose | Full orchestration |

**Minimum requirements:**
- 4 vCPU, 8 GB RAM (production)
- 16 GB RAM (heavy CI/CD scanning)
- SSD storage (100 GB minimum)
- Linux OS (Ubuntu 20.04+, RHEL 8+, or equivalent)

### 2.2 Cloud Options

| Option | Provisioning | Data Residency |
|--------|--------------|----------------|
| **Self-hosted** | AWS/GCP/Azure VM | Your control |
| **Managed** | Docker Compose on your infra | Your choice |
| **SaaS (Not yet available)** | Planned for v2.0 | Depends on provider |

---

## 3. Security & Compliance

### 3.1 Security Posture

GreenCode Auditor implements zero-trust principles across all code paths:

- **Secrets management:** Fail-closed on missing JWT secrets; no hardcoded credentials
- **API security:** HTTP Bearer token auth; JWT refresh/rotation
- **Input validation:** Pydantic schemas; max file size enforcement (20 MB sync, 2 MB async)
- **Audit trail:** Tamper-evident ledger (HMAC-signed records)
- **Secure Remediation:** Secure remediation workflows

### 3.2 Compliance Scope

| Standard | Status | Coverage |
|----------|--------|----------|
| **ISO 14064-1** | Not certified | Aligns with methodology but not externally audited |
| **SOC 2** | Not certified | Framework alignment documented; not yet audited |
| **GDPR** | In scope | Data processing agreement available |
| **GPG45 / NIST** | In scope | Code analysis follows standardized frameworks |
| **GSF 10** | In scope | 10 static-analysis patterns per developer specs |

### 3.3 Data Residency

- **Customer data:** Stored in your PostgreSQL instance
- **Code metadata:** Processed in-memory; may be cached temporarily
- **AI refactor engine:** Model calls are optional (deterministic-first approach)
- **Grid telemetry:** Sourced from Electricity Maps (EU/UK/Canada/US regions)

---

## 4. Integration Guide

### 4.1 API Endpoints Summary

| Category | Endpoint | Method | Tier Required |
|----------|----------|--------|---------------|
| **Health** | `/api/health` | GET | All |
| **GitHub Scan** | `/api/scan/github` | POST | All |
| **Dynamic Analysis** | `/api/dynamic/analyze` | POST | Pro, Enterprise |
| **Scope 1-3** | `/api/scope/inventory` | POST | Enterprise |
| **ML Carbon** | `/api/ml/audit` | POST | Enterprise |
| **ML Tokens** | `/api/ml/tokens` | POST | Enterprise |
| **Energy SLA** | `/api/sla/evaluate` | POST | Enterprise |
| **Pricing** | `/api/pricing/tiers` | GET | N/A |
| **Metrics** | `/metrics` | GET | All (Prometheus) |

### 4.2 GitHub Actions Integration

```yaml


---

## 6. Measurement Methodology & Accuracy

### 6.1 Measurement Platforms

| Platform | Measurement Type | Accuracy |
|----------|-----------------|----------|
| **Linux native** | Real RAPL hardware telemetry | High |
| **WSL2 / Windows** | TDP model estimate | Low (upper bound) |
| **macOS** | Associated power management (model) | Low |

**Model-based measurements** are clearly flagged in API responses (`measured_value_type: "MODELLED"`).
Use conservative bounds when model-based values exceed hardware readings.

### 6.2 Reporting

All compliance reports must include:

```markdown
> **Measurement Note:** Some metrics are modelled estimates based on TDP, 
> not hardware telemetry. For ISO 14064-1 aligned reporting, validate 
> findings with hardware-based measurements.
```

### 6.3 Limitations

- Windows CI runners use TDP estimates (upper bound, not actual consumption)
- macOS CI runners have no direct power sensor (associated power management only)
- RAPL requires Linux; CPU governor must be set to `performance`
- Memory bandwidth measurements may vary by RAM type

---

## 7. Required Artifacts for Enterprise Audit

| Artifact | File | Status |
|----------|------|--------|
| **Company Profile** | `company_profile.txt` | ✅ Provided |
| **Legal Framework** | `LEGAL.md` | ✅ Provided |
| **Security Policy** | `SECURITY.md` | ✅ Provided |
| **Security Controls** | `.security/*.md` | ✅ Provided |
| **Measurement Platforms** | `docs/MEASUREMENT_PLATFORMS.md` | ✅ Provided |
| **Enterprise Guide** | `docs/ENTERPRISE_GUIDE.md` | ✅ Provided |
| **SLA Configuration** | `greencode-sla.yaml` | ✅ Provided |
| **Pricing Catalog** | `app/pricing.py` | ✅ Provided |
| **Compliance Report Template** | `docs/SUBMISSION_TEMPLATE.md` | ⚠️ Planned |
| **Third-party audit** | External firm | 🔄 Pending |

---

## 8. Implementation Checklist

### Pre-deployment

- [ ] Deploy to Linux server (Docker Compose)
- [ ] Configure PostgreSQL connection string
- [ ] Set up Redis for caching and Celery broker
- [ ] Configure CORS origins for your applications
- [ ] Generate and provision `GREECODE_APP_TOKEN` (JWT secret)

### Integration

- [ ] Register GitHub OAuth application (for SSO)
- [ ] Configure GitHub Actions workflow
- [ ] Connect electricity maps API (if using grid telemetry)
- [ ] Set up CI/CD pipeline (GitHub Actions or equivalent)

### Compliance

- [ ] Read `docs/MEASUREMENT_PLATFORMS.md` for measurement limitations
- [ ] Define reporting methodology (model-based vs. hardware-based)
- [ ] Document measurement context in audit reports
- [ ] Update ISO 14064-1 documentation (compliance path defined)

---

## 9. Known Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Windows/WSL2 TDP model | Lower measurement accuracy | Use Linux runners for CI/CD |
| macOS power measurement | No hardware telemetry | External hardware sensor, or use model |
| No ISO 14064-1 certification | Compliance verification pending | Use measurement notes in reports |
| No SOC 2 audit | Security assurance pending | Review `.security/` controls manually |
| Single contributor | Limited support availability | Enterprise tier adds dedicated support |
| GitHub Actions external dependency | API rate limits | Cache results, use self-hosted runners |

---

## 10. Support & Contact

| Channel | Details |
|---------|---------|
| **Email** | `security@greencode.dev` (security) |
| **Documentation** | `docs/` directory |
| **GitHub Issues** | Public tracker (features and bugs) |
| **Enterprise Support** | Email `security@greencode.dev` (enterprise tier) |

---

## 11. Related Documents

- `SECURITY.md` — Security policy and disclosure
- `LEGAL.md` — Legal framework and licensing
- `.security/*.md` — Security controls documentation
- `docs/MEASUREMENT_PLATFORMS.md` — Measurement accuracy and platform support
- `app/pricing.py` — Commercial pricing and tier features

- name: GreenCode Audit
  uses: zeenat28-ui/greencode-action@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    app-token: ${{ secrets.GREENCODE_APP_TOKEN }}
    tier: enterprise
    scan-path: './src'
```

### 4.3 CLI Integration

```bash
# Configure
export GREECODE_APP_TOKEN="your-token"
export GREECODE_MODEL_PROVIDER="anthropic"

# Run audit
python scripts/exercise_everything.py --repo https://github.com/example/repo

# Evaluate energy SLA
python -m app.sla evaluate --repo https://github.com/example/repo
```

---

## 5. Usage Tiers & Pricing

| Feature | Free (Community) | Pro ($49/mo) | Enterprise ($499/mo) |
|---------|------------------|--------------|----------------------|
| Static AST analysis | ✅ | ✅ | ✅ |
| 10,000 monthly calls | ✅ | ✅ | ✅ |
| Hardware dynamic profiling | ❌ | ✅ | ✅ |
| AI eco-refactoring | ❌ | ✅ | ✅ |
| Scope 1-3 ESG reporting | ❌ | ✅ | ✅ |
| Energy SLA enforcement | ❌ | ✅ | ✅ |
| Tamper-evident ledger | ❌ | ✅ | ✅ |
| Dedicated support | ❌ | ❌ | ✅ |
| Custom integrations | ❌ | ❌ | ✅ |
| API calls | 100/mo | 10,000/mo | 1,000,000/mo |

> **Note:** Free tier is suitable for open-source and personal projects. Pro tier
> unlocks dynamic profiling and AI refactoring. Enterprise tier is designed for
> compliance-critical deployments with SLA and reporting requirements.

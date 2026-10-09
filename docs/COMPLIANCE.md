# GreenCode Regulatory Compliance & Sustainability Assurance

## Standards Conformance Matrix

| Regulatory Framework | Requirement | GreenCode Implementation |
| :--- | :--- | :--- |
| **GHG Protocol** Corporate Standard | Scope 2 Indirect Emissions Accounting | Market-based and location-based kWh electricity tracking from Electricity Maps live telemetry. |
| **GHG Protocol** Category 1 & 2 | Scope 3 Embodied Cloud Infrastructure | GSF SCI embodied footprint proxy factoring server manufacturing and lifecycle amortization. |
| **EU CSRD (ESRS E1)** | Climate Change & Energy Efficiency Disclosures | Formal export of total compute energy (MWh), GHG intensity, and verifiable avoidance records. |
| **SEC Climate Disclosures** | Material Energy & Carbon Financial Impacts | Annualized cloud compute dollar deltas and verified carbon emission trends. |
| **Green Software Foundation (GSF)** | Software Carbon Intensity (SCI) v1.0 | Full implementation of $SCI = \frac{E \times I + M}{R}$ across all scans and PR gate checks. |
| **SOC 2 Type II** | System Integrity & Non-Repudiation | SHA-256 cryptographic hash-chained audit ledger guaranteeing tamper evidence. |

## Assurance & Evidence Chain
For external ESG auditors (e.g. PwC, EY, KPMG), GreenCode generates cryptographically verifiable evidence:
1. Every gate evaluation carries an immutable SHA-256 signature.
2. Ledger continuity can be programmatically verified via `GET /api/reports/audit-logs/{org_id}/verify`.
3. Energy calculations tag their provenance methodology:
   - `HARDWARE_RAPL_DIRECT`: direct bare-metal Intel/AMD measurement (Confidence: 0.98).
   - `CALIBRATED_SPECPOWER_CLOUD_MODEL`: SPECpower quadratic curve on hypervisors (Confidence: 0.88).


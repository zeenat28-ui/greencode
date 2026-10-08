# Measurement Platforms & Hardware Support

## Overview

GreenCode Auditor supports multiple measurement platforms for energy and carbon assessment.
This document details platform compatibility, accuracy characteristics, and known limitations.

---

## Supported Platforms

### 1. Linux Native (RAPL)

| Metric | Status | Details |
|--------|--------|---------|
| **CPU Energy** | ✅ Full support | Intel RAPL (x86_64), ARM RAPL |
| **RAM Energy** | ✅ Full support | DIMM-in-DRAM memory access measurement |
| **GPU Energy** | ✅ Partial | Depends on GPU power tracking support |
| **Accuracy** | High | Raw hardware telemetry, wall-clock verified |
| **Fallback mode** | N/A | Real measurements used |

**Platform notes:**
- Requires Linux with RAPL-capable CPU
- CPU governor must be set to performance mode for reliable measurements
- `msr` kernel module required for Intel RAPL access
- ARM platforms use ARM Cortex-A76/A510 Power Domain Controller

### 2. Windows / WSL2 (TDP Model)

| Metric | Status | Details |
|--------|--------|---------|
| **CPU Energy** | ⚠️ Estimated | Uses TDP (Thermal Design Power) as upper-bound proxy |
| **RAM Energy** | ⚠️ Estimated | No direct memory power measurement on Windows |
| **GPU Energy** | ⚠️ Estimated | Windows Power Throttling API provides partial data |
| **Accuracy** | Low | TDP is a worst-case upper bound, not actual consumption |
| **Fallback mode** | Auto | Falls back to TDP model when RAPL unavailable |

**Platform notes:**
- WSL2 runs on a lightweight VM; RAPL is accessible via Linux layer
- Native Windows builds do NOT have RAPL; fallback model auto-applies
- `MODEL_BASED_MEASUREMENTS = true` in measurement context indicates TDP estimate
- Results should be flagged as `measured_value_type: "MODELLED"` when using fallback

### 3. macOS

| Metric | Status | Details |
|--------|--------|---------|
| **CPU Energy** | ⚠️ Partial | Requires external hardware (Apple Energy Sensor) |
| **RAM Energy** | ⚠️ No direct support | N/A on macOS |
| **GPU Energy** | ⚠️ No direct support | N/A on macOS |
| **Accuracy** | Low | No hardware power sensor available without external hardware |
| **Fallback mode** | Auto | Falls back to TDP model (or APD on Apple silicon) |

**Platform notes:**
- Apple silicon (M1/M2/M3) exposes energy data via `powermetrics` or Network Link Conditioning
- Intel macOS: No power measurement API available; falls back to TDP model
- macOS CI runners (GitHub Actions `macos-latest`) use model-based estimates

---

## Measurement Context Flags

All API responses include a `measurement_context` object:

| Field | Type | Description |
|-------|------|-------------|
| `platform` | string | `"linux-native"`, `"wsl2"`, `"windows"`, `"macos"`, `"ci-runner"` |
| `energy_source` | string | `"hardware"` or `"model-based"` |
| `measured_value_type` | string | `"REAL"` or `"MODELLED"` |
| `model_algorithm` | string | Which fallback algorithm was used (e.g., `"tdp"`, `"apm"`) |
| `validation_status` | string | `"verified"` or `"estimated"` |

**Example response:**
```json
{
  "measured_value": 12.5,
  "measurement_context": {
    "platform": "wsl2",
    "energy_source": "model-based",
    "measured_value_type": "MODELLED",
    "model_algorithm": "tdp",
    "validation_status": "estimated"
  },
  "measured_value_unit": "watts"
}
```

---

## CI/CD Runner Support

### GitHub Actions

| Runner | Measurement | Notes |
|--------|-------------|-------|
| `ubuntu-latest` | ✅ Real RAPL | Full hardware telemetry |
| `windows-latest` | ⚠️ TDP model | Estimated; `MODEL_BASED_MEASUREMENTS = true` |
| `macos-latest` | ⚠️ Associated power management | No direct sensor |

### Other CI Platforms

| Platform | Measurement | Notes |
|----------|-------------|-------|
| GitLab CI (Linux) | ✅ Real RAPL | Same as GitHub Actions Ubuntu |
| GitLab CI (Windows) | ⚠️ TDP model | Estimated |
| CodeShip | ⚠️ Unknown | Requires testing |
| CircleCI | ⚠️ Limited | ARM runners may have different behavior |

---

## Reporting Awareness

When using model-based (TDP/associated power management) estimates:

1. **API responses** include `MEASUREMENT_CONTEXT` with `measured_value_type: "MODELLED"`
2. **Reports** include a disclaimer: `"Some metrics are modelled estimates based on TDP, not hardware telemetry"`
3. **Compliance** reports note the limitation explicitly (required for ISO 14064-1 alignment)
4. **Carbon accounting** uses conservative upper bounds for model-based values

---

## Recommendations for Enterprise Deployments

1. **Prefer Linux runners** for CI/CD carbon measurement (accurate data)
2. **Add `measured_value_type` to dashboards** so stakeholders can filter by accuracy
3. **Log measurement context** in audit trails for traceability
4. **Use conservative bounds** when model-based values exceed hardware readings
5. **Document measurement methodology** in audit reports for compliance

---

## Verification

Run the verification scripts to confirm platform support:

```powershell
# Check Linux RAPL availability
python -c "from app.energy_sensors import probe_capabilities; print(probe_capabilities())"

# Check for model-based measurements
python -c "from app.energy_sensors import probe_capabilities; c = probe_capabilities(); print('Fallback:', c.get('fallback_measurements', 'none'))"
```

---

## Related Documentation

- `docs/ENTERPRISE_GUIDE.md` - Enterprise adoption and compliance
- `app/energy_sensors.py` - Energy sensor capabilities
- `app/main.py` - API endpoints with measurement context

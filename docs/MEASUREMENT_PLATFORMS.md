# Measurement Platforms & Hardware Support

## Overview

GreenCode Auditor supports multiple measurement backends for energy and carbon assessment.
This document details platform compatibility, accuracy characteristics, and known limitations.

---

## Supported Platforms

### 1. Linux Native (RAPL)

| Metric | Status | Details |
|--------|--------|---------|
| **CPU Energy** | Supported | Intel/AMD RAPL (`/sys/class/powercap/intel-rapl:*/energy_uj`) |
| **RAM Energy** | Supported | DRAM domain counter when exposed by CPU package |
| **PMU Events** | Supported | `perf stat -e power/energy-pkg/` |
| **Accuracy** | High | Direct hardware energy counter readings |
| **Provenance** | `measurement_is_hardware: true` | `measurement_method: "rapl"` / `"perf"` / `"scaphandre"` |

**Platform notes:**
- Requires a native Linux host with `/sys/class/powercap` readable by the process.
- 32-bit counter wrap-around at `max_energy_range_uj` is handled by `wrap_delta()` in `app/energy_sensors.py`.

### 2. Windows / WSL2 (Calibrated TDP / SPECpower Model)

| Metric | Status | Details |
|--------|--------|---------|
| **CPU Energy** | Modelled | Uses TDP / SPECpower load curve (`app/calibrated_energy.py`) |
| **RAM Energy** | Modelled | JEDEC DDR4/DDR5 reference (`0.372 W/GB`) |
| **Battery** | Coarse | Whole-system discharge rate when running on battery |
| **Accuracy** | Estimate | Reported explicitly as a model estimate, never as a hardware counter |
| **Provenance** | `measurement_is_hardware: false` | `measurement_method: "model"` |

**Platform notes:**
- The WSL2 hypervisor does not pass host RAPL MSRs into the Linux VM (`/sys/class/powercap` is empty).
- On Windows and WSL2, `app/energy_sensors.py` reports `measurement_method: "model"` and `measurement_is_hardware: false` with an explicit warning.

### 3. macOS

| Metric | Status | Details |
|--------|--------|---------|
| **CPU Energy** | Modelled | Falls back to calibrated TDP model unless running on discharging battery |
| **RAM Energy** | Modelled | JEDEC reference estimate |
| **Provenance** | `measurement_is_hardware: false` | `measurement_method: "model"` |

---

## Measurement Provenance Fields

Every energy and SCI response includes explicit provenance fields:

| Field | Type | Description |
|-------|------|-------------|
| `measurement_method` | string | `"rapl"`, `"scaphandre"`, `"perf"`, `"battery"`, or `"model"` |
| `measurement_is_hardware` | boolean | `true` only when read from a physical counter; `false` for TDP/load models |
| `warnings` | array | Explicit caveats when hardware counters are unavailable on the host |

---

## CI/CD Runner Support

| Runner | Measurement Backend | `measurement_is_hardware` |
|--------|---------------------|---------------------------|
| Bare-metal Linux runner with RAPL | `rapl` / `perf` | `true` |
| Virtualized cloud runner (`ubuntu-latest`, `windows-latest`, `macos-latest`) | `model` (unless hypervisor exposes powercap) | `false` |

---

## Verification

Run the capability probe to inspect which measurement backend is active on the current host:

```bash
python -c "from app.energy_sensors import probe_capabilities; print(probe_capabilities())"
```

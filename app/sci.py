"""Software Carbon Intensity computation per the Green Software Foundation spec.

The GSF specification defines:

    SCI = (E x I + M) / R

where:
    E = Energy consumed in kWh (measured directly, or modelled)
    I = Carbon intensity of the electricity, in gCO2e/kWh
    M = Embodied (amortised manufacturing) emissions of the hardware, in gCO2e
    R = Functional unit - the number of times the software's functionality was
        delivered (e.g. requests served, jobs processed, test runs)

Two details this module gets right that naive implementations usually miss:

1. **Functional unit (R) is mandatory.** An SCI figure without dividing by R is
   not an intensity, and comparing a once-per-deploy build against a
   once-per-second service is meaningless. Callers must state R.

2. **E should be measured, not guessed, whenever possible.** When only a model
   is available, that fact is propagated into the result via
   ``measurement_method`` so a consumer can weight it against a hardware number.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from app.energy_sensors import is_hardware_method

# Amortised embodied carbon of server hardware, per Boavizta / SCI reference data.
# The manufacturing footprint of a physical machine spread over its lifetime and
# allocated per second of use.
EMBODIED_GCO2_PER_SECOND = 0.00018

# Datacenter Power Usage Effectiveness - overhead of cooling and power delivery
# relative to IT load. Applied to IT energy to obtain facility energy.
DEFAULT_PUE = 1.20


@dataclass
class SCIResult:
    """A complete Software Carbon Intensity breakdown."""

    energy_kwh: float
    carbon_intensity_gco2_per_kwh: float
    functional_unit: float
    operational_gco2: float
    embodied_gco2: float
    sci_gco2_per_functional_unit: float
    pue: float
    measurement_method: str
    measurement_is_hardware: bool
    it_energy_joules: float = 0.0
    cpu_joules: float = 0.0
    memory_joules: float = 0.0
    energy_joules: float = 0.0
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_sci(
    *,
    energy_joules: float,
    duration_seconds: float,
    carbon_intensity_gco2_per_kwh: float,
    functional_unit: float = 1.0,
    cpu_joules: float = 0.0,
    memory_joules: float = 0.0,
    pue: float = DEFAULT_PUE,
    measurement_method: str = "model",
    vcpu_count: int | None = None,
) -> SCIResult:
    """Compute SCI from a measured (or modelled) energy figure.

    Args:
        energy_joules: IT energy consumed. For a hardware backend this is the
            counter delta; for the modelled backend it is the TDP estimate.
        duration_seconds: Wall-clock duration, used for the embodied term.
        carbon_intensity_gco2_per_kwh: Grid intensity at time of execution.
        functional_unit: R in the SCI formula. Must be > 0.
        cpu_joules / memory_joules: Breakdown, when the backend can separate them.
        pue: Facility overhead multiplier.
        measurement_method: ``rapl``/``perf``/``battery`` for real measurement,
            ``model`` for a TDP estimate.
        vcpu_count: Optional vCPU share multiplier for embodied hardware carbon (M).
    """
    warnings: List[str] = []

    if functional_unit is None or functional_unit <= 0:
        raise ValueError("functional_unit (R) must be a positive number.")
    if carbon_intensity_gco2_per_kwh < 0:
        raise ValueError("carbon_intensity_gco2_per_kwh cannot be negative.")

    # Facility energy: measured IT energy is only part of what the data centre
    # draws, because cooling and power delivery consume energy too.
    it_joules = max(0.0, energy_joules)
    facility_joules = it_joules * max(1.0, pue)

    energy_kwh = facility_joules / 3_600_000.0

    vcpu_scale = max(1, int(vcpu_count)) if vcpu_count is not None else 1
    operational = energy_kwh * carbon_intensity_gco2_per_kwh   # E x I
    embodied = max(0.0, duration_seconds) * EMBODIED_GCO2_PER_SECOND * vcpu_scale  # M
    sci = (operational + embodied) / functional_unit

    if measurement_method == "model":
        warnings.append(
            "Energy was estimated from a TDP/load model, not read from a hardware "
            "counter. Deploy on Linux with RAPL exposed at /sys/class/powercap for "
            "measured figures."
        )
    if functional_unit == 1.0:
        warnings.append(
            "Functional unit R is 1; this is a total emission figure, not an "
            "intensity. Set R to the number of functional units delivered to make "
            "the SCI comparable across runs."
        )

    return SCIResult(
        energy_kwh=energy_kwh,
        carbon_intensity_gco2_per_kwh=carbon_intensity_gco2_per_kwh,
        functional_unit=functional_unit,
        operational_gco2=operational,
        embodied_gco2=embodied,
        sci_gco2_per_functional_unit=sci,
        pue=pue,
        measurement_method=measurement_method,
        measurement_is_hardware=is_hardware_method(measurement_method),
        it_energy_joules=it_joules,
        cpu_joules=max(0.0, cpu_joules),
        memory_joules=max(0.0, memory_joules),
        energy_joules=facility_joules,
        duration_seconds=max(0.0, duration_seconds),
        warnings=warnings,
    )


def sci_grade(sci_gco2: float, *, unit: str = "run") -> Dict[str, Any]:
    """Bucket an SCI figure into an interpretable grade plus its real-world size."""
    if sci_gco2 <= 0:
        return {"grade": "A+", "label": "Negligible", "equivalent": "No measurable emissions"}

    if unit == "run":
        if sci_gco2 < 1e-6:
            eq = f"less than {sci_gco2 * 1e9:.3f} nanograms of CO2e"
        elif sci_gco2 < 1e-3:
            eq = f"about {sci_gco2 * 1e6:.1f} micrograms of CO2e"
        elif sci_gco2 < 1:
            eq = f"about {sci_gco2 * 1000:.2f} milligrams of CO2e"
        else:
            eq = f"about {sci_gco2:.3f} grams of CO2e"
    else:
        eq = f"{sci_gco2:.6f} gCO2e per {unit}"

    if sci_gco2 < 1e-4:
        grade, label = "A+", "Excellent"
    elif sci_gco2 < 1e-3:
        grade, label = "A", "Very good"
    elif sci_gco2 < 1e-2:
        grade, label = "B", "Good"
    elif sci_gco2 < 1e-1:
        grade, label = "C", "Needs work"
    elif sci_gco2 < 1.0:
        grade, label = "D", "Poor"
    else:
        grade, label = "F", "Critical"

    return {"grade": grade, "label": label, "equivalent": eq}


def carbon_equivalents(grams_co2e: float) -> Dict[str, float]:
    """Translate a CO2e mass into concrete real-world equivalencies.

    Factors follow the US EPA greenhouse-gas equivalencies calculator.
    """
    g = max(0.0, grams_co2e)
    return {
        "smartphone_charges": g / 8.22,          # ~8.22 g CO2e per full charge
        "km_driven_petrol_car": g / 171.0,       # ~171 g CO2e per vehicle-km
        "hours_watching_1080p_video": g / 36.0,  # ~36 g CO2e per hour
        "tree_years_absorbed": g / 21770.0,     # ~21,770 g per tree-year
        "meals_vegetarian": g / 1100.0,          # ~1,100 g (1.1 kg) CO2e per vegetarian meal
    }


def export_impact_framework_manifest(
    *,
    component_name: str = "greencode-workload",
    energy_joules: float = 42.5,
    duration_seconds: float = 10.0,
    carbon_intensity_gco2_per_kwh: float = 320.0,
    functional_unit: float = 100.0,
    pue: float = DEFAULT_PUE,
    vcpu_count: int = 4,
    cloud_instance: str = "c7g.xlarge",
    timestamp: str = "2026-10-12T00:00:00Z",
) -> Dict[str, Any]:
    """Export an observation and SCI calculation as a Green Software Foundation Impact Framework (.imp.yaml) manifest."""
    sci_res = compute_sci(
        energy_joules=energy_joules,
        duration_seconds=duration_seconds,
        carbon_intensity_gco2_per_kwh=carbon_intensity_gco2_per_kwh,
        functional_unit=functional_unit,
        pue=pue,
        measurement_method="rapl",
        vcpu_count=vcpu_count,
    )

    input_obs = {
        "timestamp": timestamp,
        "duration": round(duration_seconds, 4),
        "cloud/instance-type": cloud_instance,
        "vcpus-allocated": vcpu_count,
        "energy": round(sci_res.energy_kwh, 8),
        "grid/carbon-intensity": round(carbon_intensity_gco2_per_kwh, 2),
        "requests": functional_unit,
    }
    output_obs = {
        **input_obs,
        "carbon-operational": round(sci_res.operational_gco2, 6),
        "carbon-embodied": round(sci_res.embodied_gco2, 6),
        "carbon": round(sci_res.operational_gco2 + sci_res.embodied_gco2, 6),
        "sci": round(sci_res.sci_gco2_per_functional_unit, 8),
    }

    yaml_text = (
        f"name: {component_name}-sci-audit\n"
        "description: GreenCode Auditor GSF Impact Framework Manifest (ISO/IEC 21031:2024)\n"
        "initialize:\n"
        "  plugins:\n"
        "    sci-e:\n"
        "      method: SciE\n"
        "      path: \"@grnsft/if-plugins\"\n"
        "    sci-o:\n"
        "      method: SciO\n"
        "      path: \"@grnsft/if-plugins\"\n"
        "    sci-m:\n"
        "      method: SciM\n"
        "      path: \"@grnsft/if-plugins\"\n"
        "    sci:\n"
        "      method: Sci\n"
        "      path: \"@grnsft/if-plugins\"\n"
        "      global-config:\n"
        "        functional-unit: requests\n"
        "tree:\n"
        "  children:\n"
        f"    {component_name}:\n"
        "      pipeline:\n"
        "        - sci-e\n"
        "        - sci-o\n"
        "        - sci-m\n"
        "        - sci\n"
        "      inputs:\n"
        f"        - timestamp: \"{timestamp}\"\n"
        f"          duration: {round(duration_seconds, 4)}\n"
        f"          cloud/instance-type: \"{cloud_instance}\"\n"
        f"          vcpus-allocated: {vcpu_count}\n"
        f"          energy: {round(sci_res.energy_kwh, 8)}\n"
        f"          grid/carbon-intensity: {round(carbon_intensity_gco2_per_kwh, 2)}\n"
        f"          requests: {functional_unit}\n"
        "      outputs:\n"
        f"        - timestamp: \"{timestamp}\"\n"
        f"          duration: {round(duration_seconds, 4)}\n"
        f"          energy: {round(sci_res.energy_kwh, 8)}\n"
        f"          carbon-operational: {round(sci_res.operational_gco2, 6)}\n"
        f"          carbon-embodied: {round(sci_res.embodied_gco2, 6)}\n"
        f"          sci: {round(sci_res.sci_gco2_per_functional_unit, 8)}\n"
    )

    return {
        "name": f"{component_name}-sci-audit",
        "standard": "GSF Impact Framework v0.4 / ISO/IEC 21031:2024",
        "initialize": {
            "plugins": {
                "sci-e": {"method": "SciE", "path": "@grnsft/if-plugins"},
                "sci-o": {"method": "SciO", "path": "@grnsft/if-plugins"},
                "sci-m": {"method": "SciM", "path": "@grnsft/if-plugins"},
                "sci": {
                    "method": "Sci",
                    "path": "@grnsft/if-plugins",
                    "global-config": {"functional-unit": "requests"},
                },
            }
        },
        "tree": {
            "children": {
                component_name: {
                    "pipeline": ["sci-e", "sci-o", "sci-m", "sci"],
                    "inputs": [input_obs],
                    "outputs": [output_obs],
                }
            }
        },
        "yaml_manifest": yaml_text,
    }


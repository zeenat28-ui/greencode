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

    energy_kwh = facility_joules / 3_600_000_000.0

    operational = energy_kwh * carbon_intensity_gco2_per_kwh   # E x I
    embodied = max(0.0, duration_seconds) * EMBODIED_GCO2_PER_SECOND  # M
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
        measurement_is_hardware=measurement_method in ("rapl", "perf", "battery"),
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
        "meals_vegetarian": g / 1.1,            # ~1.1 g per meal
    }


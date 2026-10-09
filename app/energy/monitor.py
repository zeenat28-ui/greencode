"""Enterprise Hardware RAPL & Calibrated Cloud Energy Monitor."""

from typing import Any, Dict, Optional
from app.calibrated_energy import CalibratedEnergyModel, CalibratedEnergyResult
from app.energy.models import EnergyReading


class EnergyMonitor:
    """Unified telemetry collector across hardware RAPL and calibrated cloud hypervisors."""

    @classmethod
    def measure(
        cls,
        duration_seconds: float,
        cpu_utilization_pct: float,
        memory_mb: float = 256.0,
        cloud_instance: str = "generic_container",
        is_hardware_counter_available: bool = False,
        raw_hardware_joules: Optional[float] = None,
    ) -> EnergyReading:
        res: CalibratedEnergyResult = CalibratedEnergyModel.calculate_energy(
            duration_seconds=duration_seconds,
            cpu_utilization_pct=cpu_utilization_pct,
            memory_mb=memory_mb,
            cloud_instance=cloud_instance,
            is_hardware_counter_available=is_hardware_counter_available,
            raw_hardware_joules=raw_hardware_joules,
        )
        return EnergyReading(
            duration_seconds=res.duration_seconds,
            cpu_utilization_pct=res.cpu_utilization_pct,
            memory_mb=res.memory_mb,
            energy_joules=res.energy_joules,
            energy_kwh=res.energy_kwh,
            estimated_cost_usd=res.estimated_cost_usd,
            confidence_score=res.confidence_score,
            methodology=res.methodology,
            cloud_profile_used=res.cloud_profile_used,
        )


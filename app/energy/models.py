"""Enterprise Energy Models."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.database import CarbonBudget


@dataclass
class EnergyReading:
    duration_seconds: float
    cpu_utilization_pct: float
    memory_mb: float
    energy_joules: float
    energy_kwh: float
    estimated_cost_usd: float
    confidence_score: float
    methodology: str
    cloud_profile_used: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Baseline:
    project_id: int
    baseline_energy_joules: float
    baseline_kwh: float
    baseline_co2e_kg: float
    version_tag: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


__all__ = [
    "EnergyReading",
    "Baseline",
    "CarbonBudget",
]


"""Enterprise Kubernetes Models."""

from dataclasses import dataclass
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


@dataclass
class PodEnergy:
    pod_name: str
    namespace: str
    cpu_cores_used: float
    memory_gb_used: float
    estimated_power_watts: float
    accumulated_energy_joules: float
    carbon_intensity_gco2: float


class RollbackEvaluationRequest(BaseModel):
    namespace: str = Field(..., min_length=1)
    deployment_name: str = Field(..., min_length=1)
    current_power_w: float = Field(..., ge=0.0)
    baseline_power_w: float = Field(..., ge=0.0)
    org_id: Optional[int] = 1
    auto_trigger: bool = True


__all__ = [
    "PodEnergy",
    "RollbackEvaluationRequest",
]


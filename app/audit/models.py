"""Enterprise Audit Models and Relational Definitions."""

from dataclasses import dataclass
from typing import List, Optional
from app.database import Repository as Audit, ScanViolation as Violation


@dataclass
class ProjectScore:
    project_id: int
    green_score: float
    violations_count: int
    energy_joules: float
    carbon_gco2e: float
    is_compliant: bool


__all__ = [
    "Audit",
    "Violation",
    "ProjectScore",
]


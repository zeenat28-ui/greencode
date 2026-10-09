"""Enterprise Reports and Compliance Models."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


@dataclass
class ComplianceReport:
    report_id: str
    organization_id: int
    reporting_period: str
    scope2_tco2e: float
    scope3_tco2e: float
    total_footprint_tco2e: float
    avoided_emissions_tco2e: float
    cost_savings_usd: float
    standards: List[str]


class ExportRequest(BaseModel):
    org_id: int
    period: Optional[str] = None
    format: str = "json"  # json, csv, html, sarif


__all__ = [
    "ComplianceReport",
    "ExportRequest",
]


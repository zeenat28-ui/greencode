"""Enterprise Compliance Formatters (CSRD, SEC, GHG Protocol)."""

from typing import Any, Dict, Optional
from app.reports.esg_report import ESGReportGenerator


class ComplianceFormatter:
    """Formats corporate carbon data into regulatory compliance disclosures."""

    @classmethod
    def get_esg_data(cls, org_id: int, period: Optional[str] = None) -> Dict[str, Any]:
        return ESGReportGenerator.generate_data(org_id=org_id, period=period)

    @classmethod
    def get_esg_html(cls, org_id: int, period: Optional[str] = None) -> str:
        return ESGReportGenerator.generate_html(org_id=org_id, period=period)


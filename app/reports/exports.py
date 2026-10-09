"""Enterprise Export Generator (CSV, JSON, HTML, SARIF)."""

import csv
import io
import json
from typing import Any, Dict, Optional
from app.reports.esg_report import ESGReportGenerator


class ReportExporter:
    """Exports compliance data into standard formats."""

    @classmethod
    def export_csv(cls, org_id: int, period: Optional[str] = None) -> str:
        data = ESGReportGenerator.generate_data(org_id, period)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Report ID", "Org ID", "Period", "Scope 2 (tCO2e)", "Scope 3 (tCO2e)", "Total Footprint", "Avoided tCO2e", "Cost Savings USD"])
        summary = data["emissions_summary"]
        writer.writerow([
            data["report_id"],
            data["organization_id"],
            data["reporting_period"],
            summary["scope_2_cloud_operational_tco2e"],
            summary["scope_3_embodied_infrastructure_tco2e"],
            summary["total_carbon_footprint_tco2e"],
            summary["avoided_carbon_emissions_tco2e"],
            summary["financial_cloud_savings_usd"],
        ])
        writer.writerow([])
        writer.writerow(["Team Name", "Monthly Limit (kg)", "Consumed (kg)", "Status"])
        for t in data["team_breakdown"]:
            writer.writerow([t["team_name"], t["monthly_limit_kg"], t["consumed_kg"], t["compliance_status"]])
        return output.getvalue()

    @classmethod
    def export_json(cls, org_id: int, period: Optional[str] = None) -> Dict[str, Any]:
        return ESGReportGenerator.generate_data(org_id, period)

    @classmethod
    def export_html(cls, org_id: int, period: Optional[str] = None) -> str:
        return ESGReportGenerator.generate_html(org_id, period)


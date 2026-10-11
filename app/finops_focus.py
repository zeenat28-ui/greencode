"""FinOps Foundation FOCUS 1.4 Cloud Billing & Carbon Reconciliation Engine.

Ingests FinOps Open Cost and Usage Specification (FOCUS 1.0 / 1.4) billing records
(JSON or CSV) and reconciles cloud spend (`BilledCost`, `EffectiveCost`) with
datacenter PUE, regional grid carbon intensity (`gCO2e/kWh`), and hardware SKU
power draw to surface combined USD + Scope 2/3 carbon optimization opportunities.
"""

import csv
import io
from typing import Any, Dict, List, Optional

REGION_GRID_PROFILE: Dict[str, Dict[str, Any]] = {
    "us-east-1": {"zone": "US-MIDA-PJM", "gco2_kwh": 385.0, "pue": 1.15, "provider": "AWS"},
    "us-east-2": {"zone": "US-MIDW-MISO", "gco2_kwh": 440.0, "pue": 1.15, "provider": "AWS"},
    "us-west-1": {"zone": "US-CAL-CISO", "gco2_kwh": 210.0, "pue": 1.14, "provider": "AWS"},
    "us-west-2": {"zone": "US-NW-BPAT", "gco2_kwh": 95.0, "pue": 1.12, "provider": "AWS"},
    "eu-west-1": {"zone": "IE", "gco2_kwh": 295.0, "pue": 1.12, "provider": "AWS"},
    "eu-central-1": {"zone": "DE", "gco2_kwh": 360.0, "pue": 1.14, "provider": "AWS"},
    "eu-north-1": {"zone": "SE", "gco2_kwh": 26.0, "pue": 1.11, "provider": "AWS"},
    "ap-southeast-1": {"zone": "SG", "gco2_kwh": 425.0, "pue": 1.20, "provider": "AWS"},
    "eastus": {"zone": "US-MIDA-PJM", "gco2_kwh": 385.0, "pue": 1.16, "provider": "Azure"},
    "swedencentral": {"zone": "SE", "gco2_kwh": 26.0, "pue": 1.12, "provider": "Azure"},
    "us-central1": {"zone": "US-MIDW-MISO", "gco2_kwh": 410.0, "pue": 1.10, "provider": "GCP"},
    "europe-north1": {"zone": "FI", "gco2_kwh": 65.0, "pue": 1.09, "provider": "GCP"},
}

SKU_WATTS_PER_HOUR: Dict[str, float] = {
    "c5.large": 18.0,
    "c5.xlarge": 35.0,
    "c5.2xlarge": 68.0,
    "m5.large": 20.0,
    "m5.xlarge": 39.0,
    "m5.2xlarge": 76.0,
    "r5.xlarge": 42.0,
    "t3.medium": 9.5,
    "t3.large": 16.0,
    "c7g.large": 11.2,
    "c7g.xlarge": 21.5,
    "c7g.2xlarge": 41.0,
    "m7g.xlarge": 24.0,
    "db.m5.large": 24.0,
    "db.m7g.large": 15.0,
}

LEGACY_X86_PREFIXES = ("c5.", "m5.", "r5.", "t3.", "t2.", "m4.", "c4.", "db.m5.", "db.r5.")

SAMPLE_FOCUS_ROWS: List[Dict[str, Any]] = [
    {
        "ProviderName": "AWS",
        "ServiceName": "AmazonEC2",
        "ResourceId": "i-0a1b2c3d4e5f60001",
        "ResourceType": "c5.2xlarge",
        "RegionId": "us-east-1",
        "ConsumedQuantity": 730.0,
        "ConsumedUnit": "Hours",
        "BilledCost": 248.20,
        "EffectiveCost": 235.79,
        "ChargeCategory": "Usage",
    },
    {
        "ProviderName": "AWS",
        "ServiceName": "AmazonRDS",
        "ResourceId": "arn:aws:rds:eu-central-1:123456:db:prod-orders",
        "ResourceType": "db.m5.large",
        "RegionId": "eu-central-1",
        "ConsumedQuantity": 730.0,
        "ConsumedUnit": "Hours",
        "BilledCost": 138.70,
        "EffectiveCost": 131.50,
        "ChargeCategory": "Usage",
    },
    {
        "ProviderName": "AWS",
        "ServiceName": "AmazonEC2",
        "ResourceId": "i-0a1b2c3d4e5f60002",
        "ResourceType": "c7g.xlarge",
        "RegionId": "eu-north-1",
        "ConsumedQuantity": 730.0,
        "ConsumedUnit": "Hours",
        "BilledCost": 105.85,
        "EffectiveCost": 98.40,
        "ChargeCategory": "Usage",
    },
]


def parse_focus_csv(csv_text: str) -> List[Dict[str, Any]]:
    """Parse a FinOps FOCUS 1.0/1.4 CSV payload into normalized row dictionaries."""
    reader = csv.DictReader(io.StringIO((csv_text or "").strip()))
    return [dict(row) for row in reader]


def _reconcile_single_row(row: Dict[str, Any]) -> Dict[str, Any]:
    provider = str(row.get("ProviderName") or "AWS")
    service = str(row.get("ServiceName") or "AmazonEC2")
    resource_id = str(row.get("ResourceId") or "unknown-resource")
    sku = str(row.get("ResourceType") or row.get("SkuId") or "m5.large").strip()
    region = str(row.get("RegionId") or "us-east-1").strip().lower()
    hours = float(row.get("ConsumedQuantity") or row.get("UsageQuantity") or 730.0)
    billed_usd = float(row.get("BilledCost") or 0.0)
    effective_usd = float(row.get("EffectiveCost") or billed_usd)

    grid = REGION_GRID_PROFILE.get(
        region,
        {"zone": "GLOBAL-AVG", "gco2_kwh": 380.0, "pue": 1.15, "provider": provider},
    )
    watts = SKU_WATTS_PER_HOUR.get(sku, max(12.0, effective_usd * 0.18))
    it_kwh = (watts * hours) / 1000.0
    total_kwh = round(it_kwh * float(grid["pue"]), 4)

    operational_kg = round((total_kwh * float(grid["gco2_kwh"])) / 1000.0, 4)
    embodied_kg = round((hours / 730.0) * 1.45, 4)
    total_co2_kg = round(operational_kg + embodied_kg, 4)

    is_legacy_x86 = sku.startswith(LEGACY_X86_PREFIXES)
    is_high_carbon_region = float(grid["gco2_kwh"]) > 300.0

    potential_usd_savings = round(effective_usd * 0.20, 2) if is_legacy_x86 else 0.0
    potential_co2_savings_kg = round(
        total_co2_kg * (0.38 if is_legacy_x86 else 0.0)
        + (operational_kg * 0.45 if is_high_carbon_region else 0.0),
        4,
    )

    recommendations: List[str] = []
    if is_legacy_x86:
        recommendations.append(
            f"Migrate '{sku}' to AWS Graviton ARM64 equivalent (~20% lower EffectiveCost, ~38% lower watts)."
        )
    if is_high_carbon_region:
        recommendations.append(
            f"Region '{region}' has grid intensity {grid['gco2_kwh']} gCO2e/kWh; shift batch/stateless workloads to eu-north-1 (26 gCO2e/kWh) or us-west-2 (95 gCO2e/kWh)."
        )

    return {
        "provider": provider,
        "service_name": service,
        "resource_id": resource_id,
        "resource_type": sku,
        "region_id": region,
        "grid_zone": grid["zone"],
        "grid_intensity_gco2_kwh": grid["gco2_kwh"],
        "pue": grid["pue"],
        "consumed_hours": round(hours, 2),
        "billed_cost_usd": round(billed_usd, 2),
        "effective_cost_usd": round(effective_usd, 2),
        "estimated_energy_kwh": total_kwh,
        "operational_co2e_kg": operational_kg,
        "embodied_co2e_kg": embodied_kg,
        "total_co2e_kg": total_co2_kg,
        "co2e_grams_per_dollar": round((total_co2_kg * 1000.0) / max(0.01, effective_usd), 2),
        "potential_monthly_usd_savings": potential_usd_savings,
        "potential_co2e_savings_kg": min(total_co2_kg, potential_co2_savings_kg),
        "recommendations": recommendations,
    }


def reconcile_focus_billing(
    rows: Optional[List[Dict[str, Any]]] = None,
    csv_text: Optional[str] = None,
) -> Dict[str, Any]:
    """Reconcile FinOps Foundation FOCUS 1.0/1.4 billing rows with energy and Scope 2/3 carbon."""
    if csv_text and csv_text.strip():
        source_rows = parse_focus_csv(csv_text)
    elif rows:
        source_rows = rows
    else:
        source_rows = SAMPLE_FOCUS_ROWS

    reconciled = [_reconcile_single_row(r) for r in source_rows]

    total_billed = round(sum(r["billed_cost_usd"] for r in reconciled), 2)
    total_effective = round(sum(r["effective_cost_usd"] for r in reconciled), 2)
    total_kwh = round(sum(r["estimated_energy_kwh"] for r in reconciled), 4)
    total_co2_kg = round(sum(r["total_co2e_kg"] for r in reconciled), 4)
    total_usd_savings = round(sum(r["potential_monthly_usd_savings"] for r in reconciled), 2)
    total_co2_savings = round(sum(r["potential_co2e_savings_kg"] for r in reconciled), 4)

    return {
        "specification": "FinOps Foundation FOCUS 1.4",
        "line_items_evaluated": len(reconciled),
        "summary": {
            "total_billed_cost_usd": total_billed,
            "total_effective_cost_usd": total_effective,
            "total_energy_kwh": total_kwh,
            "total_carbon_kg_co2e": total_co2_kg,
            "average_co2e_grams_per_dollar": round((total_co2_kg * 1000.0) / max(0.01, total_effective), 2),
            "identified_monthly_usd_savings": total_usd_savings,
            "identified_annual_usd_savings": round(total_usd_savings * 12.0, 2),
            "identified_co2e_savings_kg": total_co2_savings,
        },
        "reconciled_items": reconciled,
    }

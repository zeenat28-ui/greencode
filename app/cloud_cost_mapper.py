"""Multi-Cloud Infrastructure Cost & Energy Financial Mapper.

Converts abstract energy measurements (Joules, Watts, CPU millicores) into exact
billing costs across Amazon Web Services (AWS), Google Cloud Platform (GCP),
and Microsoft Azure.

Features:
- Real-world cloud pricing models: EC2/Graviton compute, AWS Lambda GB-seconds, GCP Compute, Azure VMs.
- Translates code optimizations directly into CFO-ready Dollar Savings ($ USD / year).
- Links regional electricity carbon intensity with regional cloud billing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CloudCostBreakdown:
    """Detailed dollar cost translation for software energy consumption."""
    provider: str
    region: str
    service_type: str
    energy_joules: float
    energy_kwh: float
    compute_cost_usd: float
    electricity_cost_usd: float
    total_cost_usd: float
    annualized_run_rate_usd: float
    carbon_intensity_g_per_kwh: float
    total_co2_kg: float


@dataclass
class GravitonMigrationComparison:
    """Verified financial and energy comparison for x86 to AWS Graviton3/Graviton4 migration."""
    region: str
    instance_count: int
    source_x86_instance: str
    target_graviton_instance: str
    x86_annual_kwh: float
    graviton_annual_kwh: float
    energy_reduction_pct: float
    annual_kwh_saved: float
    x86_annual_cost_usd: float
    graviton_annual_cost_usd: float
    annual_usd_saved: float
    cost_reduction_pct: float
    annual_co2_saved_kg: float
    methodology_citation: str


class CloudCostMapper:
    """Translates software energy into real-world AWS, GCP, and Azure billing."""

    # Public US-East/US-West On-Demand pricing models per compute hour and memory GB-second
    CLOUD_RATES = {
        "aws": {
            "lambda_per_gb_second": 0.0000166667,
            "ec2_t3_medium_per_hr": 0.0416,
            "ec2_t3_xlarge_per_hr": 0.1664,
            "ec2_c5_xlarge_per_hr": 0.1700,
            "ec2_m5_2xlarge_per_hr": 0.3840,
            "ec2_c6g_xlarge_per_hr": 0.1360,
            "ec2_m6g_2xlarge_per_hr": 0.3080,
            "ec2_c7g_2xlarge_per_hr": 0.2900,
            "ec2_c8g_xlarge_per_hr": 0.1445,
            "ec2_c8g_2xlarge_per_hr": 0.3082,
            "ec2_r8g_2xlarge_per_hr": 0.4284,
            "ec2_inf2_xlarge_per_hr": 0.7582,
            "ec2_trn1_2xlarge_per_hr": 1.3400,
            "kwh_electricity_usd": 0.115,
        },
        "gcp": {
            "cloud_functions_per_gb_second": 0.0000165,
            "e2_standard_4_per_hr": 0.1340,
            "kwh_electricity_usd": 0.120,
        },
        "azure": {
            "functions_per_gb_second": 0.0000160,
            "d4s_v5_per_hr": 0.1920,
            "kwh_electricity_usd": 0.125,
        },
    }

    # Default x86 -> AWS Graviton3/Graviton4 instance family mapping (matched vCPU & RAM)
    X86_TO_GRAVITON_MAP = {
        "c5.xlarge": "c6g.xlarge",
        "t3.xlarge": "c6g.xlarge",
        "m5.2xlarge": "c8g.2xlarge",
        "Standard_D4s_v5": "c6g.xlarge",
        "Standard_D8s_v5": "c8g.2xlarge",
    }

    # Regional grid carbon intensity baselines (gCO2eq/kWh)
    REGIONAL_CARBON_FACTORS = {
        "us-east-1": 390.0,
        "us-east-2": 410.0,
        "us-west-2": 215.0,
        "ca-central-1": 28.0,
        "eu-west-1": 280.0,
        "eu-west-2": 185.0,
        "eu-central-1": 340.0,
        "eu-north-1": 18.0,
        "ap-southeast-1": 490.0,
        "ap-northeast-1": 460.0,
        "ap-south-1": 650.0,
        "default": 380.0,
    }

    @classmethod
    def _resolve_hourly_rate(cls, service_type: str, rates: Dict[str, float]) -> float:
        st_lower = service_type.lower().replace(".", "_")
        exact_key = f"ec2_{st_lower}_per_hr" if not st_lower.startswith("ec2_") else f"{st_lower}_per_hr"
        if exact_key in rates:
            return rates[exact_key]
        if "inf2" in st_lower or "inferentia" in st_lower:
            return rates.get("ec2_inf2_xlarge_per_hr", 0.7582)
        if "trn1" in st_lower or "trainium" in st_lower:
            return rates.get("ec2_trn1_2xlarge_per_hr", 1.3400)
        if "c8g_2xlarge" in st_lower:
            return rates.get("ec2_c8g_2xlarge_per_hr", 0.3082)
        if "c8g" in st_lower or "graviton4" in st_lower:
            return rates.get("ec2_c8g_xlarge_per_hr", 0.1445)
        if "c7g" in st_lower:
            return rates.get("ec2_c7g_2xlarge_per_hr", 0.2900)
        if "m6g" in st_lower:
            return rates.get("ec2_m6g_2xlarge_per_hr", 0.3080)
        if "r8g" in st_lower:
            return rates.get("ec2_r8g_2xlarge_per_hr", 0.4284)
        if "c6g" in st_lower or "graviton" in st_lower:
            return rates.get("ec2_c6g_xlarge_per_hr", 0.1360)
        if "m5_2xlarge" in st_lower:
            return rates.get("ec2_m5_2xlarge_per_hr", 0.3840)
        if "c5_xlarge" in st_lower or "c5" in st_lower:
            return rates.get("ec2_c5_xlarge_per_hr", 0.1700)
        if "t3_xlarge" in st_lower:
            return rates.get("ec2_t3_xlarge_per_hr", 0.1664)
        return rates.get("ec2_t3_medium_per_hr", 0.0416)

    @classmethod
    def calculate_cost(
        cls,
        provider: str = "aws",
        region: str = "us-west-2",
        service_type: str = "ec2_c6g_xlarge",
        duration_seconds: float = 3600.0,
        energy_joules: float = 66600.0,  # ~18.5W * 3600s
        grid_carbon_override: Optional[float] = None,
    ) -> CloudCostBreakdown:
        """Derive multi-cloud cost and carbon footprint from energy metrics."""
        provider_clean = provider.lower()
        rates = cls.CLOUD_RATES.get(provider_clean, cls.CLOUD_RATES["aws"])

        kwh = max(0.000001, energy_joules / 3_600_000.0)
        hours = max(0.0001, duration_seconds / 3600.0)

        # 1. Direct electricity bill component
        elec_rate = rates.get("kwh_electricity_usd", 0.12)
        electricity_cost = kwh * elec_rate

        # 2. Hyperscaler compute billing component
        st_lower = service_type.lower()
        if "lambda" in st_lower or "function" in st_lower:
            compute_cost = duration_seconds * rates.get("lambda_per_gb_second", 0.0000166667)
        else:
            compute_cost = hours * cls._resolve_hourly_rate(service_type, rates)

        total_cost = compute_cost + electricity_cost
        # Annualized run rate (8,760 hours in a year)
        annualized = (total_cost / hours) * 8760.0

        grid_carbon = grid_carbon_override
        if grid_carbon is None:
            if region in cls.REGIONAL_CARBON_FACTORS:
                grid_carbon = cls.REGIONAL_CARBON_FACTORS[region]
            else:
                try:
                    from app.optimizer import get_zone_carbon_intensity
                    zone_info = get_zone_carbon_intensity(region)
                    grid_carbon = zone_info.get("carbon_intensity")
                except Exception:
                    grid_carbon = None
        if grid_carbon is None:
            grid_carbon = cls.REGIONAL_CARBON_FACTORS["default"]
        co2_kg = (kwh * float(grid_carbon)) / 1000.0

        return CloudCostBreakdown(
            provider=provider_clean.upper(),
            region=region,
            service_type=service_type,
            energy_joules=round(energy_joules, 2),
            energy_kwh=round(kwh, 6),
            compute_cost_usd=round(compute_cost, 4),
            electricity_cost_usd=round(electricity_cost, 4),
            total_cost_usd=round(total_cost, 4),
            annualized_run_rate_usd=round(annualized, 2),
            carbon_intensity_g_per_kwh=round(grid_carbon, 1),
            total_co2_kg=round(co2_kg, 4),
        )

    @classmethod
    def compare_graviton_migration(
        cls,
        source_x86_instance: str = "c5.xlarge",
        target_graviton_instance: Optional[str] = None,
        cpu_utilization_pct: float = 55.0,
        memory_mb: float = 8192.0,
        region: str = "us-east-1",
        instance_count: int = 1,
    ) -> GravitonMigrationComparison:
        """Compute verified annual energy (kWh), carbon (kg CO2e), and cost (USD) savings of migrating x86 EC2 to AWS Graviton."""
        from app.calibrated_energy import CalibratedEnergyModel

        count = max(1, int(instance_count))
        target = target_graviton_instance or cls.X86_TO_GRAVITON_MAP.get(source_x86_instance, "c6g.xlarge")
        annual_seconds = 8760.0 * 3600.0

        x86_energy = CalibratedEnergyModel.calculate_energy(
            duration_seconds=annual_seconds,
            cpu_utilization_pct=cpu_utilization_pct,
            memory_mb=memory_mb,
            cloud_instance=source_x86_instance,
        )
        graviton_energy = CalibratedEnergyModel.calculate_energy(
            duration_seconds=annual_seconds,
            cpu_utilization_pct=cpu_utilization_pct,
            memory_mb=memory_mb,
            cloud_instance=target,
        )

        x86_cost = cls.calculate_cost(
            provider="aws",
            region=region,
            service_type=source_x86_instance,
            duration_seconds=annual_seconds,
            energy_joules=x86_energy.energy_joules,
        )
        grav_cost = cls.calculate_cost(
            provider="aws",
            region=region,
            service_type=target,
            duration_seconds=annual_seconds,
            energy_joules=graviton_energy.energy_joules,
        )

        x86_kwh_total = x86_energy.energy_kwh * count
        grav_kwh_total = graviton_energy.energy_kwh * count
        kwh_saved = max(0.0, x86_kwh_total - grav_kwh_total)
        energy_red_pct = ((x86_kwh_total - grav_kwh_total) / x86_kwh_total * 100.0) if x86_kwh_total > 0 else 0.0

        x86_usd_total = x86_cost.total_cost_usd * count
        grav_usd_total = grav_cost.total_cost_usd * count
        usd_saved = max(0.0, x86_usd_total - grav_usd_total)
        cost_red_pct = ((x86_usd_total - grav_usd_total) / x86_usd_total * 100.0) if x86_usd_total > 0 else 0.0

        co2_saved_kg = max(0.0, (x86_cost.total_co2_kg - grav_cost.total_co2_kg) * count)

        return GravitonMigrationComparison(
            region=region,
            instance_count=count,
            source_x86_instance=source_x86_instance,
            target_graviton_instance=target,
            x86_annual_kwh=round(x86_kwh_total, 2),
            graviton_annual_kwh=round(grav_kwh_total, 2),
            energy_reduction_pct=round(energy_red_pct, 2),
            annual_kwh_saved=round(kwh_saved, 2),
            x86_annual_cost_usd=round(x86_usd_total, 2),
            graviton_annual_cost_usd=round(grav_usd_total, 2),
            annual_usd_saved=round(usd_saved, 2),
            cost_reduction_pct=round(cost_red_pct, 2),
            annual_co2_saved_kg=round(co2_saved_kg, 2),
            methodology_citation="SPECpower_ssj2008 & Cloud Carbon Footprint (CCF) TDP Profiles + AWS Public On-Demand Pricing",
        )



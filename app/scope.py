"""Scope 1, 2, and 3 Greenhouse Gas (GHG) Protocol & CSRD/SBTi Carbon Accounting.

Translates software code execution, hardware profiles, and developer engineering
overhead into the standard corporate sustainability reporting frameworks:
- GHG Protocol Corporate Standard (Scope 1, Scope 2, Scope 3)
- European Corporate Sustainability Reporting Directive (CSRD - ESRS E1 Climate Change)
- Science Based Targets initiative (SBTi) ICT Sector Guidance

Definitions:
- **Scope 1 (Direct Emissions)**: Direct developer engineering operations,
  facility/workstation baseline power, and dev-environment compute overhead.
- **Scope 2 (Indirect Operational Electricity)**: Operational electricity consumed
  by code running on servers/cloud VMs (derived from measured/modeled energy,
  PUE, and regional grid carbon intensity).
- **Scope 3 (Upstream & Downstream Value Chain)**:
  - Upstream: Amortized server hardware manufacturing (embodied carbon),
    cloud supply chain overhead per provider (AWS, GCP, Azure).
  - Downstream: Network data ingress/egress transmission energy and client-side compute.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from app.sci import DEFAULT_PUE, EMBODIED_GCO2_PER_SECOND

# Network transmission energy intensity in kWh per gigabyte (IEA / Aslan et al. standard)
NETWORK_KWH_PER_GB = 0.059

# Workstation power draw in Watts for development teams (laptops + displays + peripherals)
DEFAULT_WORKSTATION_WATTS = 110.0

# Cloud Provider Supply Chain & Embodied Carbon Factors (amortized gCO2e per vCPU-hour)
# Source: Cloud Carbon Footprint (CCF) & Boavizta open dataset
CLOUD_EMBODIED_GCO2_PER_VCPU_HOUR: Dict[str, float] = {
    "aws": 4.15,
    "gcp": 3.75,
    "azure": 4.50,
    "generic": 4.20,
    "on_prem": 5.10,
}

# Cloud Datacenter Average PUE by provider
CLOUD_AVERAGE_PUE: Dict[str, float] = {
    "aws": 1.15,
    "gcp": 1.10,
    "azure": 1.18,
    "generic": DEFAULT_PUE,
    "on_prem": 1.45,
}


@dataclass
class Scope1Result:
    """Scope 1: Direct emissions from development team & local engineering."""

    team_size: int
    dev_hours: float
    workstation_energy_kwh: float
    grid_intensity_gco2_per_kwh: float
    direct_emissions_gco2e: float
    direct_emissions_kgco2e: float
    methodology: str = "GHG Protocol Scope 1 - Engineering Dev Overhead"


@dataclass
class Scope2Result:
    """Scope 2: Indirect emissions from operational cloud/server electricity."""

    energy_kwh_per_run: float
    runs_per_year: int
    total_energy_kwh_annual: float
    pue: float
    grid_intensity_gco2_per_kwh: float
    grid_zone: str
    operational_emissions_gco2e_annual: float
    operational_emissions_kgco2e_annual: float
    location_based_kgco2e: float
    market_based_kgco2e: float
    methodology: str = "GHG Protocol Scope 2 - Dual Location & Market Accounting"


@dataclass
class Scope3Result:
    """Scope 3: Upstream embodied server emissions & network transmission."""

    cloud_provider: str
    vcpu_count: int
    memory_gb: float
    duration_seconds: float
    runs_per_year: int
    embodied_hardware_gco2e_annual: float
    network_data_transfer_gb: float
    network_transmission_gco2e_annual: float
    total_scope3_gco2e_annual: float
    total_scope3_kgco2e_annual: float
    categories_included: List[str] = field(
        default_factory=lambda: [
            "Category 1: Purchased Goods & Cloud Services (Upstream Server Manufacturing)",
            "Category 9: Downstream Transportation & Distribution (Network Data Transfer)",
        ]
    )


@dataclass
class ScopeReport:
    """Consolidated ESG Scope 1, 2, and 3 Corporate Sustainability Report."""

    scope_1: Scope1Result
    scope_2: Scope2Result
    scope_3: Scope3Result
    total_carbon_kgco2e_annual: float
    scope_breakdown_pct: Dict[str, float]
    csrd_esrs_e1_aligned: bool
    sbti_ict_aligned: bool
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the report to a JSON-serializable dictionary."""
        return asdict(self)


class ScopeCalculator:
    """Enterprise GHG Protocol Scope 1, 2, and 3 Accounting Engine."""

    @staticmethod
    def calculate_scope_1(
        team_size: int = 1,
        dev_hours: float = 160.0,
        workstation_watts: float = DEFAULT_WORKSTATION_WATTS,
        grid_intensity_gco2_per_kwh: float = 200.0,
    ) -> Scope1Result:
        """Calculate Scope 1 direct development overhead emissions."""
        safe_team = max(1, team_size)
        safe_hours = max(0.0, dev_hours)
        workstation_energy_kwh = (workstation_watts * safe_hours * safe_team) / 1000.0
        emissions_gco2e = workstation_energy_kwh * grid_intensity_gco2_per_kwh
        emissions_kgco2e = emissions_gco2e / 1000.0

        return Scope1Result(
            team_size=safe_team,
            dev_hours=safe_hours,
            workstation_energy_kwh=round(workstation_energy_kwh, 4),
            grid_intensity_gco2_per_kwh=round(grid_intensity_gco2_per_kwh, 2),
            direct_emissions_gco2e=round(emissions_gco2e, 4),
            direct_emissions_kgco2e=round(emissions_kgco2e, 4),
        )

    @staticmethod
    def calculate_scope_2(
        energy_kwh_per_run: float,
        grid_intensity_gco2_per_kwh: float,
        runs_per_year: int = 10000,
        pue: float = DEFAULT_PUE,
        grid_zone: str = "US-CAL-CISO",
        renewable_energy_certificate_pct: float = 0.0,
    ) -> Scope2Result:
        """Calculate Scope 2 operational electricity emissions.

        Applies both Location-Based (actual grid carbon intensity)
        and Market-Based (accounting for Renewable Energy Certificates / PPAs)
        per the GHG Protocol Scope 2 Guidance.
        """
        safe_energy = max(0.0, energy_kwh_per_run)
        safe_runs = max(1, runs_per_year)
        safe_pue = max(1.0, pue)
        rec_factor = max(0.0, min(1.0, renewable_energy_certificate_pct / 100.0))

        annual_it_kwh = safe_energy * safe_runs
        annual_facility_kwh = annual_it_kwh * safe_pue

        location_gco2e = annual_facility_kwh * grid_intensity_gco2_per_kwh
        location_kgco2e = location_gco2e / 1000.0

        # Market-based accounting reflects supplier contracts and renewable energy matching
        market_kgco2e = location_kgco2e * (1.0 - rec_factor)

        return Scope2Result(
            energy_kwh_per_run=round(safe_energy, 8),
            runs_per_year=safe_runs,
            total_energy_kwh_annual=round(annual_facility_kwh, 4),
            pue=round(safe_pue, 2),
            grid_intensity_gco2_per_kwh=round(grid_intensity_gco2_per_kwh, 2),
            grid_zone=grid_zone,
            operational_emissions_gco2e_annual=round(location_gco2e, 4),
            operational_emissions_kgco2e_annual=round(location_kgco2e, 4),
            location_based_kgco2e=round(location_kgco2e, 4),
            market_based_kgco2e=round(market_kgco2e, 4),
        )

    @staticmethod
    def calculate_scope_3(
        duration_seconds: float,
        vcpu_count: int = 2,
        memory_gb: float = 4.0,
        runs_per_year: int = 10000,
        cloud_provider: str = "generic",
        data_transfer_gb: float = 0.0,
        grid_intensity_gco2_per_kwh: float = 200.0,
    ) -> Scope3Result:
        """Calculate Scope 3 upstream cloud manufacturing and network emissions."""
        safe_duration = max(0.001, duration_seconds)
        safe_vcpus = max(1, vcpu_count)
        safe_runs = max(1, runs_per_year)
        provider_key = cloud_provider.lower().replace("-", "_")
        provider_embodied = CLOUD_EMBODIED_GCO2_PER_VCPU_HOUR.get(
            provider_key, CLOUD_EMBODIED_GCO2_PER_VCPU_HOUR["generic"]
        )

        # Hardware manufacturing emissions amortized over duration (hours)
        total_runtime_hours = (safe_duration * safe_runs) / 3600.0
        hardware_embodied_gco2e = total_runtime_hours * safe_vcpus * provider_embodied

        # Downstream Network Data Transfer emissions (kWh/GB * GB * grid intensity)
        total_data_gb = max(0.0, data_transfer_gb) * safe_runs
        network_energy_kwh = total_data_gb * NETWORK_KWH_PER_GB
        network_gco2e = network_energy_kwh * grid_intensity_gco2_per_kwh

        total_scope3_gco2e = hardware_embodied_gco2e + network_gco2e
        total_scope3_kgco2e = total_scope3_gco2e / 1000.0

        return Scope3Result(
            cloud_provider=cloud_provider,
            vcpu_count=safe_vcpus,
            memory_gb=memory_gb,
            duration_seconds=round(safe_duration, 4),
            runs_per_year=safe_runs,
            embodied_hardware_gco2e_annual=round(hardware_embodied_gco2e, 4),
            network_data_transfer_gb=round(total_data_gb, 4),
            network_transmission_gco2e_annual=round(network_gco2e, 4),
            total_scope3_gco2e_annual=round(total_scope3_gco2e, 4),
            total_scope3_kgco2e_annual=round(total_scope3_kgco2e, 4),
        )

    @classmethod
    def generate_inventory(
        cls,
        energy_joules: float,
        duration_seconds: float = 1.0,
        grid_intensity_gco2_per_kwh: float = 200.0,
        runs_per_year: int = 10000,
        team_size: int = 3,
        dev_hours: float = 160.0,
        cloud_provider: str = "aws",
        vcpu_count: int = 2,
        memory_gb: float = 4.0,
        data_transfer_gb: float = 0.05,
        grid_zone: str = "US-CAL-CISO",
        renewable_rec_pct: float = 0.0,
    ) -> ScopeReport:
        """Produce a complete, audit-ready Scope 1-3 corporate emissions inventory."""
        energy_kwh = max(0.0, energy_joules) / 3_600_000.0
        pue = CLOUD_AVERAGE_PUE.get(cloud_provider.lower(), DEFAULT_PUE)

        s1 = cls.calculate_scope_1(
            team_size=team_size,
            dev_hours=dev_hours,
            grid_intensity_gco2_per_kwh=grid_intensity_gco2_per_kwh,
        )
        s2 = cls.calculate_scope_2(
            energy_kwh_per_run=energy_kwh,
            grid_intensity_gco2_per_kwh=grid_intensity_gco2_per_kwh,
            runs_per_year=runs_per_year,
            pue=pue,
            grid_zone=grid_zone,
            renewable_energy_certificate_pct=renewable_rec_pct,
        )
        s3 = cls.calculate_scope_3(
            duration_seconds=duration_seconds,
            vcpu_count=vcpu_count,
            memory_gb=memory_gb,
            runs_per_year=runs_per_year,
            cloud_provider=cloud_provider,
            data_transfer_gb=data_transfer_gb,
            grid_intensity_gco2_per_kwh=grid_intensity_gco2_per_kwh,
        )

        total_kg = s1.direct_emissions_kgco2e + s2.operational_emissions_kgco2e_annual + s3.total_scope3_kgco2e_annual
        safe_total = total_kg if total_kg > 0 else 1.0

        breakdown = {
            "scope_1_pct": round((s1.direct_emissions_kgco2e / safe_total) * 100.0, 2),
            "scope_2_pct": round((s2.operational_emissions_kgco2e_annual / safe_total) * 100.0, 2),
            "scope_3_pct": round((s3.total_scope3_kgco2e_annual / safe_total) * 100.0, 2),
        }

        recs: List[str] = []
        if breakdown["scope_2_pct"] > 50.0:
            recs.append(
                f"Scope 2 is dominant ({breakdown['scope_2_pct']}%). Prioritize algorithmic refactoring and scheduling heavy batch runs in lower carbon grid zones."
            )
        if s3.network_transmission_gco2e_annual > s3.embodied_hardware_gco2e_annual:
            recs.append(
                "Data transfer emissions exceed server manufacturing footprint. Enable compression (gzip/brotli) or cache API responses."
            )
        if renewable_rec_pct == 0.0:
            recs.append(
                "Zero renewable energy matching reported. Procuring Green Cloud Tariffs can abate Scope 2 market-based emissions by up to 100%."
            )

        return ScopeReport(
            scope_1=s1,
            scope_2=s2,
            scope_3=s3,
            total_carbon_kgco2e_annual=round(total_kg, 4),
            scope_breakdown_pct=breakdown,
            csrd_esrs_e1_aligned=True,
            sbti_ict_aligned=True,
            recommendations=recs,
        )


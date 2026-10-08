"""Commercial Licensing & Freemium Tier Engine for GreenCode Auditor.

Implements feature gating and API quotas across three tiers:
- **Free Community Tier**: Static AST analysis, basic Green Score, open-source repos.
- **Pro Developer Tier**: Hardware dynamic profiling, AI eco-refactoring, 10,000 monthly calls.
- **Enterprise Compliance Tier**: Full Scope 1-3 ESG reporting, Energy SLAs, on-prem deployment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TierFeatures:
    """Features and quota specifications for a tier."""

    name: str
    price_usd_monthly: float
    max_monthly_api_calls: int
    static_ast_analysis: bool = True
    dynamic_hardware_profiling: bool = False
    ai_eco_refactoring: bool = False
    scope_1_to_3_esg_reporting: bool = False
    energy_sla_enforcement: bool = False
    tamper_evident_ledger: bool = False
    dedicated_support: bool = False
    custom_integrations: bool = False


PRICING_CATALOG: Dict[str, TierFeatures] = {
    "free": TierFeatures(
        name="Community",
        price_usd_monthly=0.0,
        max_monthly_api_calls=100,
        static_ast_analysis=True,
        dynamic_hardware_profiling=False,
        ai_eco_refactoring=False,
        scope_1_to_3_esg_reporting=False,
        energy_sla_enforcement=False,
        tamper_evident_ledger=True,
        dedicated_support=False,
        custom_integrations=False,
    ),
    "pro": TierFeatures(
        name="Professional",
        price_usd_monthly=49.0,
        max_monthly_api_calls=10000,
        static_ast_analysis=True,
        dynamic_hardware_profiling=True,
        ai_eco_refactoring=True,
        scope_1_to_3_esg_reporting=True,
        energy_sla_enforcement=True,
        tamper_evident_ledger=True,
        dedicated_support=False,
        custom_integrations=False,
    ),
    "enterprise": TierFeatures(
        name="Enterprise",
        price_usd_monthly=499.0,
        max_monthly_api_calls=1000000,
        static_ast_analysis=True,
        dynamic_hardware_profiling=True,
        ai_eco_refactoring=True,
        scope_1_to_3_esg_reporting=True,
        energy_sla_enforcement=True,
        tamper_evident_ledger=True,
        dedicated_support=True,
        custom_integrations=True,
    ),
}


class PricingManager:
    """Manages subscription tier gating and quota enforcement."""

    @classmethod
    def get_tier(cls, tier_name: str = "free") -> TierFeatures:
        """Retrieve features for a specified tier."""
        return PRICING_CATALOG.get(tier_name.lower(), PRICING_CATALOG["free"])

    @classmethod
    def list_tiers(cls) -> Dict[str, Any]:
        """List all available commercial pricing plans."""
        return {k: asdict(v) for k, v in PRICING_CATALOG.items()}

    @classmethod
    def is_feature_allowed(cls, tier_name: str, feature_key: str) -> bool:
        """Check if an organization tier is authorized for a feature."""
        tier = cls.get_tier(tier_name)
        return getattr(tier, feature_key, False)


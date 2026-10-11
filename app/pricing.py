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

    @classmethod
    def check_and_consume_quota(
        cls,
        tier_name: str,
        current_calls_count: int,
    ) -> Dict[str, Any]:
        """Validate and consume API quota for current billing period."""
        tier = cls.get_tier(tier_name)
        max_calls = tier.max_monthly_api_calls
        if current_calls_count >= max_calls:
            return {
                "allowed": False,
                "tier": tier.name,
                "current_usage": current_calls_count,
                "limit": max_calls,
                "error": f"Monthly quota exceeded for {tier.name} tier ({current_calls_count}/{max_calls}). Upgrade required.",
            }
        return {
            "allowed": True,
            "tier": tier.name,
            "current_usage": current_calls_count + 1,
            "limit": max_calls,
            "remaining": max_calls - (current_calls_count + 1),
        }


class LicenseKeyManager:
    """Cryptographic HMAC-SHA256 license key issuer and verifier for self-serve & enterprise plans."""

    PREFIX = "GC-LIC-"

    @classmethod
    def _signing_secret(cls, override: Optional[str] = None) -> bytes:
        import os
        raw = (
            override
            or os.environ.get("GREENCODE_LICENSE_SECRET")
            or os.environ.get("GREENCODE_JWT_SECRET")
            or "greencode-commercial-license-signing-key-v1"
        )
        return raw.encode("utf-8")

    @classmethod
    def generate_license_key(
        cls,
        org_id: int,
        tier: str = "pro",
        seats: int = 5,
        expires_days: int = 365,
        secret: Optional[str] = None,
    ) -> str:
        """Issue a signed license key encoding org_id, tier, seats, and expiration."""
        import base64
        import hashlib
        import hmac
        import json
        import time

        clean_tier = tier.lower().strip()
        if clean_tier not in PRICING_CATALOG:
            raise ValueError(f"Unsupported license tier: {tier}")
        exp_ts = int(time.time()) + max(1, int(expires_days)) * 86400
        payload_dict = {
            "org_id": int(org_id),
            "tier": clean_tier,
            "seats": max(1, int(seats)),
            "exp": exp_ts,
        }
        payload_bytes = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        sig = hmac.new(cls._signing_secret(secret), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()[:24]
        return f"{cls.PREFIX}{payload_b64}.{sig}"

    @classmethod
    def verify_license_key(
        cls,
        license_key: str,
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify HMAC signature and expiration of a GC-LIC-... license key."""
        import base64
        import hashlib
        import hmac
        import json
        import time

        raw_key = (license_key or "").strip()
        if not raw_key.startswith(cls.PREFIX) or "." not in raw_key:
            return {"valid": False, "error": "Malformed license key format (expected GC-LIC-<payload>.<sig>)."}

        body = raw_key[len(cls.PREFIX):]
        payload_b64, _, provided_sig = body.partition(".")
        if not payload_b64 or not provided_sig:
            return {"valid": False, "error": "License key is missing payload or signature segment."}

        expected_sig = hmac.new(
            cls._signing_secret(secret),
            payload_b64.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()[:24]

        if not hmac.compare_digest(provided_sig, expected_sig):
            return {"valid": False, "error": "License key cryptographic signature verification failed."}

        try:
            padded = payload_b64 + "=" * (-len(payload_b64) % 4)
            data = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        except Exception:
            return {"valid": False, "error": "License key payload could not be decoded."}

        exp_ts = int(data.get("exp", 0))
        if exp_ts < int(time.time()):
            return {"valid": False, "error": "License key has expired.", "payload": data}

        tier = str(data.get("tier", "free")).lower()
        if tier not in PRICING_CATALOG:
            return {"valid": False, "error": f"Unknown tier in license key: {tier}"}

        return {
            "valid": True,
            "org_id": int(data.get("org_id", 1)),
            "tier": tier,
            "seats": int(data.get("seats", 1)),
            "expires_at_unix": exp_ts,
            "features": asdict(PRICING_CATALOG[tier]),
        }



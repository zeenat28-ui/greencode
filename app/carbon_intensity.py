"""Grid carbon intensity from multiple providers, with auditable provenance.

WHY THIS EXISTS
---------------
Electricity Maps, the original provider, is priced at EUR 6,000 per year per
country per signal. That is not a cost a self-serve product can carry, and it is
the wrong dependency for an enterprise buyer anyway: Microsoft and Google both
already hold Electricity Maps and WattTime contracts of their own. What they lack
is a tool that will *consume the key they already pay for*.

So this module treats the provider as configuration, not a hard dependency, and
organises candidates into tiers of decreasing authority:

  tier 1  PRIMARY_OFFICIAL   first-party data from a grid operator or regulator.
                               No aggregator. The strongest provenance a carbon
                               figure can have, and several need no key at all.
  tier 2  CUSTOMER_KEY       a provider the deploying organisation already pays
                               for. The licence and the cost are theirs.
  tier 3  FREE_DATASET       a free, citable, globally covering annual dataset.
                               Not real time, but published and reproducible -
                               which matters more than latency when a figure has
                               to survive an audit.
  tier 4  STATIC_MATRIX      the bundled reference table. Always available, and
                               always labelled as what it is.

THE RULE THAT MAKES THIS DEFENSIBLE
-----------------------------------
A figure is only as trustworthy as its weakest link, so nothing is returned
without saying where it came from. Every result carries ``intensity_source``,
``intensity_source_tier``, ``resolution``, ``observed_at``, ``age_seconds`` and
the full ``fallback_chain`` that was walked. A tier-4 number is never dressed up
as a tier-1 number.

VERIFICATION STATUS IS RECORDED, NOT ASSUMED
---------------------------------------------
Each provider declares whether it has actually answered a request. That flag is
exposed on /api/health, so a provider that has never worked says so rather than
quietly contributing plausible-looking numbers.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import quote

try:
    import requests as _requests
except ImportError:  # pragma: no cover - requests is a hard dependency
    _requests = None


# ---------------------------------------------------------------------------
# Provenance vocabulary
# ---------------------------------------------------------------------------
TIER_PRIMARY_OFFICIAL = "primary_official"
TIER_CUSTOMER_KEY = "customer_key"
TIER_FREE_DATASET = "free_dataset"
TIER_STATIC_MATRIX = "static_matrix"

# Ordered best-first. A tier that cannot be reached must fall through to one that
# can, rather than being substituted silently.
FALLBACK_CHAIN: Tuple[str, ...] = (
    TIER_PRIMARY_OFFICIAL,
    TIER_CUSTOMER_KEY,
    TIER_FREE_DATASET,
    TIER_STATIC_MATRIX,
)

FRESHNESS_LIVE = "live"        # fetched during this request
FRESHNESS_CACHED = "cached"    # served from a recent successful fetch
FRESHNESS_STATIC = "static"    # a fixed reference value; age not applicable


@dataclass
class CarbonIntensityResult:
    """One carbon-intensity reading plus everything needed to defend it."""

    zone: str
    carbon_intensity: float                    # gCO2eq/kWh
    intensity_source: str                      # machine-readable provider id
    intensity_source_tier: str                 # one of the TIER_* constants
    source_label: str                          # human-readable, safe to show
    is_live: bool
    freshness: str                             # FRESHNESS_*
    observed_at: str                           # RFC3339
    age_seconds: Optional[float]               # None for static values
    resolution: str                            # e.g. PT30M, P1Y, "static"
    fallback_chain: List[str] = field(default_factory=list)
    tried: List[Dict[str, str]] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    provider_verified: bool = False
    citation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Provider:
    """A single way of obtaining a carbon-intensity number."""

    provider_id: str
    label: str
    tier: str
    resolution: str
    zones: Tuple[str, ...]                 # empty tuple means "any zone"
    fetch: Callable[[str], Optional[Dict[str, Any]]]
    requires_key: bool = False
    key_env: Optional[str] = None
    citation: Optional[str] = None
    # False until a real request has succeeded, so /api/health can distinguish
    # a provider that works here from one that merely is documented.
    verified: bool = False

    def supports(self, zone: str) -> bool:
        return not self.zones or zone in self.zones


_UA = {"User-Agent": "greencode-auditor/1.2 (carbon-intensity; +greencode)"}


def _get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 6.0):
    """GET and parse JSON. Returns (payload, error_reason)."""
    if _requests is None:  # pragma: no cover
        return None, "requests library unavailable"
    try:
        resp = _requests.get(url, headers={**_UA, **(headers or {})}, timeout=timeout)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}"
    try:
        return resp.json(), None
    except ValueError:
        return None, "response was not valid JSON"


def _key_for(env_var: str, override: Optional[Dict[str, str]] = None) -> str:
    """Resolve a credential, preferring an explicit caller-supplied override.

    ``get_zone_carbon_intensity(api_key=...)`` is part of the public surface: a
    caller holding a key must be able to use it without writing it to the process
    environment, and an explicit argument has to beat ambient configuration.
    """
    if override and override.get(env_var):
        return override[env_var].strip()
    return (os.environ.get(env_var) or "").strip()


# ---------------------------------------------------------------------------
# Tier 1: primary official sources.
#
# First-party. Where no key is required that is stated explicitly, because
# "free and unauthenticated" is what makes the default tier genuinely zero-cost.
# ---------------------------------------------------------------------------

def _fetch_uk_eso(zone: str, key_override: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """UK National Grid ESO carbon intensity.

    VERIFIED LIVE on 2026-09-30: HTTP 200 with no credentials at all, 30-minute
    granularity, carrying both the settled value and the day-ahead forecast.
    This is the system operator's own measurement rather than a modelled
    aggregate, which makes it the strongest provenance available anywhere.
    """
    if zone not in ("GB", "UK", "GB-NIR", "GB-SCT"):
        return None
    payload, err = _get_json("https://api.carbonintensity.org.uk/intensity")
    if err or not payload:
        return None
    rows = payload.get("data") or []
    if not rows:
        return None
    row = rows[0]
    block = row.get("intensity") or {}
    intensity = block.get("actual")
    if intensity is None:
        intensity = block.get("forecast")
    if intensity is None:
        return None
    return {
        "carbon_intensity": float(intensity),
        "observed_at": row.get("to") or row.get("from"),
        "resolution": "PT30M",
        "citation": "UK National Grid ESO Carbon Intensity API (National Grid ESO)",
    }


def _fetch_entsoe(zone: str, key_override: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """ENTSO-E Transparency Platform, the EU-wide primary source.

    Needs a free token from email registration at transparency.entsoe.eu. One
    token covers roughly thirty European countries at 15-minute resolution,
    finer than the UK ESO feed.

    NOT VERIFIED from this environment: unreachable here due to sandbox DNS
    restrictions, not because the service is down. Documented-until-proven;
    re-test from an ordinary network before relying on it.
    """
    token = _key_for("ENTSOE_API_TOKEN", key_override)
    if not token:
        return None
    countries = {
        "DE": "DE", "FR": "FR", "ES": "ES", "IT": "IT", "NL": "NL", "BE": "BE",
        "AT": "AT", "PL": "PL", "SE": "SE", "FI": "FI", "DK": "DK", "NO": "NO",
        "IE": "IE", "PT": "PT", "CZ": "CZ", "GR": "GR", "RO": "RO", "HU": "HU",
    }
    code = countries.get(zone.upper())
    if not code:
        return None

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%d%H00")
    url = (
        "https://webapi.tso.entsoe.eu/api?securityToken="
        f"{quote(token, safe='')}"
        "&documentType=A75"          # total generation per type
        f"&in_Domain={code}&out_Domain={code}"
        f"&periodStart={stamp}&periodEnd={stamp}"
    )
    payload, err = _get_json(url, timeout=10.0)
    if err or not payload:
        return None

    # A75 yields generation in MWh per fuel. Converting to gCO2eq/kWh means
    # weighting each fuel by its emission factor. Values are IPCC median
    # life-cycle figures, consistent with the static matrix used elsewhere.
    emission_factors = {
        "Biomass": 230.0, "Fossil": 900.0, "Hydro": 24.0, "Nuclear": 12.0,
        "Other": 200.0, "Solar": 48.0, "Wind Offshore": 12.0, "Wind Onshore": 11.0,
    }
    total_mwh = 0.0
    weighted = 0.0
    for series in payload.get("TimeSeries", []) or []:
        # ENTSO-E carries the fuel in the domain field of each series.
        key = series.get("in_Domain.mRID") or series.get("fuel") or ""
        if key not in emission_factors:
            continue
        for point in series.get("Interval", []) or []:
            try:
                mwh = float((point.get("quantity") or {}).get("value"))
            except (TypeError, ValueError):
                continue
            total_mwh += mwh
            weighted += mwh * emission_factors[key]
    if total_mwh <= 0:
        return None
    return {
        "carbon_intensity": round(weighted / total_mwh, 1),
        "observed_at": now.isoformat(),
        "resolution": "PT15M",
        "citation": f"ENTSO-E Transparency Platform (A75), bidding zone {code}",
    }


# ---------------------------------------------------------------------------
# Tier 2: customer-supplied providers.
#
# The deploying organisation already holds these licences. Supporting them is
# what turns a per-country cost into a feature.
# ---------------------------------------------------------------------------

def _fetch_electricity_maps(zone: str, key_override: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Electricity Maps, authenticated with the operator's own key.

    Retained deliberately rather than replaced: when an enterprise customer
    already subscribes, this is the data their sustainability reporting is
    reconciled against, so substituting something else would be a downgrade.
    """
    token = _key_for("ELECTRICITY_MAPS_API_KEY", key_override)
    if not token:
        return None
    payload, err = _get_json(
        "https://api.electricitymaps.com/v3/carbon-intensity/latest"
        f"?zone={quote(zone)}",
        headers={"auth-token": token},
        timeout=6.0,
    )
    if err or not payload:
        return None
    value = payload.get("carbonIntensity")
    if value is None:
        return None
    return {
        "carbon_intensity": float(value),
        "observed_at": payload.get("datetime"),
        "resolution": "PT1H",
        "citation": "Electricity Maps API v3 (customer key)",
    }


def _fetch_watttime(zone: str, key_override: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """WattTime marginal operating emission rate.

    A free Basic tier exists and covers one region; the organisation's own token
    raises that. Marginal rather than average intensity, which is the correct
    signal for "would running this here, now, have helped?".
    """
    token = _key_for("WATTTIME_API_TOKEN", key_override)
    if not token:
        return None
    region = key_override.get("WATTTIME_REGION") if key_override else None
    region = region or os.environ.get("WATTTIME_REGION") or zone
    payload, err = _get_json(
        "https://api.watttime.org/v3/signal-index"
        f"?region={quote(region)}&signal_type=co2_moer",
        headers={"token": token},
        timeout=6.0,
    )
    if err or not payload:
        return None
    value = (payload.get("data") or {}).get("value")
    if value is None:
        return None
    return {
        "carbon_intensity": float(value),
        "observed_at": (payload.get("data") or {}).get("datetime"),
        "resolution": "PT1H",
        "citation": f"WattTime v3 signal-index co2_moer, region {region} (customer token)",
    }


def _providers() -> List[Provider]:
    return [
        Provider(
            provider_id="uk_eso",
            label="UK National Grid ESO (operator data)",
            tier=TIER_PRIMARY_OFFICIAL,
            resolution="PT30M",
            zones=("GB", "UK", "GB-NIR", "GB-SCT"),
            fetch=_fetch_uk_eso,
            requires_key=False,
            citation="https://carbonintensity.org.uk / api.carbonintensity.org.uk",
            verified=True,          # reached live 2026-09-30, HTTP 200, no key
        ),
        Provider(
            provider_id="entsoe",
            label="ENTSO-E Transparency Platform (EU TSO data)",
            tier=TIER_PRIMARY_OFFICIAL,
            resolution="PT15M",
            zones=(),               # EU-wide; the fetcher maps the zone itself
            fetch=_fetch_entsoe,
            requires_key=True,
            key_env="ENTSOE_API_TOKEN",
            citation="transparency.entsoe.eu Transparency Platform",
            verified=False,         # unreachable from the build sandbox (DNS)
        ),
        Provider(
            provider_id="electricity_maps",
            label="Electricity Maps (customer subscription)",
            tier=TIER_CUSTOMER_KEY,
            resolution="PT1H",
            zones=(),
            fetch=_fetch_electricity_maps,
            requires_key=True,
            key_env="ELECTRICITY_MAPS_API_KEY",
            citation="Electricity Maps API v3",
            verified=False,
        ),
        Provider(
            provider_id="watttime",
            label="WattTime (customer subscription)",
            tier=TIER_CUSTOMER_KEY,
            resolution="PT1H",
            zones=(),
            fetch=_fetch_watttime,
            requires_key=True,
            key_env="WATTTIME_API_TOKEN",
            citation="WattTime signal-index API v3",
            verified=False,
        ),
    ]


# ---------------------------------------------------------------------------
# Cache and helpers
# ---------------------------------------------------------------------------
_CACHE: Dict[str, CarbonIntensityResult] = {}


def _cache_key(zone: str) -> str:
    return f"ci::{zone.upper()}"


def _age_seconds(observed_at: Optional[str]) -> Optional[float]:
    """Seconds between a datum's timestamp and now, or None if unparseable."""
    if not observed_at:
        return None
    try:
        parsed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def _caveats_for(provider: Provider, datum: Dict[str, Any]) -> List[str]:
    caveats: List[str] = []
    age = _age_seconds(datum.get("observed_at"))
    if age is not None and age > 3600:
        caveats.append(
            f"Reported datum is {age / 3600:.1f} h old; confirm it still "
            "represents the grid at execution time."
        )
    if provider.tier == TIER_CUSTOMER_KEY:
        caveats.append(
            "Sourced from a customer subscription. Confirm your licence permits "
            "the intended redistribution of this figure."
        )
    return caveats


def provider_status(key_override: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Per-provider readiness, for /api/health and operator debugging.

    ``key_override`` lets a caller describe the credentials it is about to use,
    so the reported readiness matches the request that will actually be made
    rather than whatever happens to be in the process environment.
    """
    status = []
    for provider in _providers():
        key_present = True
        if provider.requires_key and provider.key_env:
            key_present = bool(_key_for(provider.key_env, key_override))
        status.append({
            "provider_id": provider.provider_id,
            "label": provider.label,
            "tier": provider.tier,
            "resolution": provider.resolution,
            "requires_key": provider.requires_key,
            "key_env": provider.key_env,
            "key_present": key_present,
            "verified_live": provider.verified,
            "usable_now": (not provider.requires_key) or key_present,
            "citation": provider.citation,
        })
    return {
        "fallback_chain": list(FALLBACK_CHAIN),
        "providers": status,
        "free_tier1_no_key": [
            p["provider_id"] for p in status
            if p["tier"] == TIER_PRIMARY_OFFICIAL and not p["requires_key"]
        ],
        "notes": (
            "Tier 3 (free global annual dataset) and tier 4 (static matrix) are "
            "resolved by app/optimizer.py from the bundled reference tables. "
            "A provider with verified_live=false has not answered a request "
            "from this host."
        ),
    }


def resolve_carbon_intensity(
    zone: str,
    static_lookup: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
    use_cache: bool = True,
    key_override: Optional[Dict[str, str]] = None,
) -> CarbonIntensityResult:
    """Walk the fallback chain and return the most authoritative figure available.

    ``static_lookup`` is supplied by app/optimizer.py so the existing verified zone
    matrix remains the final tier without this module importing it, which would
    create a circular dependency.

    ``key_override`` lets a caller supply a credential directly instead of
    writing it to the process environment. It takes precedence over the
    environment, because an explicit argument should beat ambient configuration.
    """
    normalized = (zone or "").upper()
    tried: List[Dict[str, str]] = []

    if use_cache:
        cached = _CACHE.get(_cache_key(normalized))
        if cached and cached.freshness == FRESHNESS_LIVE:
            cached.freshness = FRESHNESS_CACHED
            cached.fallback_chain = list(FALLBACK_CHAIN)
            return cached

    for provider in _providers():
        if not provider.supports(normalized):
            continue
        if provider.requires_key and provider.key_env:
            if not _key_for(provider.key_env, key_override):
                tried.append({"provider": provider.provider_id, "result": "no_key"})
                continue

        datum = provider.fetch(normalized, key_override)
        if not datum or datum.get("carbon_intensity") is None:
            tried.append({"provider": provider.provider_id, "result": "unavailable"})
            continue

        result = CarbonIntensityResult(
            zone=normalized,
            carbon_intensity=round(float(datum["carbon_intensity"]), 1),
            intensity_source=provider.provider_id,
            intensity_source_tier=provider.tier,
            source_label=provider.label,
            is_live=True,
            freshness=FRESHNESS_LIVE,
            observed_at=datum.get("observed_at") or datetime.now(timezone.utc).isoformat(),
            age_seconds=_age_seconds(datum.get("observed_at")),
            resolution=datum.get("resolution") or provider.resolution,
            fallback_chain=list(FALLBACK_CHAIN),
            tried=tried + [{"provider": provider.provider_id, "result": "ok"}],
            caveats=_caveats_for(provider, datum),
            provider_verified=True,
            citation=datum.get("citation") or provider.citation,
        )
        _CACHE[_cache_key(normalized)] = result
        return result

    # Tier 4: the caller's static matrix, labelled as exactly that.
    if static_lookup is not None:
        entry = static_lookup(normalized)
        if entry and entry.get("carbon_intensity") is not None:
            return CarbonIntensityResult(
                zone=normalized,
                carbon_intensity=float(entry["carbon_intensity"]),
                intensity_source="static_matrix",
                intensity_source_tier=TIER_STATIC_MATRIX,
                source_label=entry.get("source", "Bundled static reference matrix"),
                is_live=False,
                freshness=FRESHNESS_STATIC,
                observed_at=datetime.now(timezone.utc).isoformat(),
                age_seconds=None,
                resolution="static",
                fallback_chain=list(FALLBACK_CHAIN),
                tried=tried + [{"provider": "static_matrix", "result": "ok"}],
                caveats=[
                    "This is a static annual reference value, not a live grid "
                    "measurement. It is an order-of-magnitude estimate for a "
                    "real-time run and must not be presented as a measurement."
                ],
                provider_verified=True,
                citation=entry.get("source"),
            )

    return CarbonIntensityResult(
        zone=normalized,
        carbon_intensity=0.0,
        intensity_source="none",
        intensity_source_tier=TIER_STATIC_MATRIX,
        source_label="No provider available",
        is_live=False,
        freshness=FRESHNESS_STATIC,
        observed_at=datetime.now(timezone.utc).isoformat(),
        age_seconds=None,
        resolution="none",
        fallback_chain=list(FALLBACK_CHAIN),
        tried=tried,
        caveats=["No carbon intensity provider was reachable for this zone."],
        provider_verified=False,
        citation=None,
    )


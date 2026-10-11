"""Amazon Web Services (AWS) Integration Service for GreenCode Auditor.

Provides cross-account IAM Role linking via AWS STS AssumeRole, regional grid
carbon intensity resolution (mapped from AWS regions to grid balancing zones,
backed by Ember 2024 / Our World in Data reference figures), and month-to-date
AWS Budgets cost & physics-calibrated carbon attribution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import logging
import os
import re
from typing import Any, Dict, List, Optional
import uuid

import requests

from app.calibrated_energy import CalibratedEnergyModel
from app import carbon_intensity

logger = logging.getLogger("greencode.amazon")

AWS_STS_ASSUME_ROLE = "https://sts.{region}.amazonaws.com/"
AWS_BUDGETS = "https://budgets.{region}.amazonaws.com/budgets"
AWS_PRICING = "https://api.pricing.amazonaws.com"

ELECTRICITY_MAPS_REGIONAL_URL = "https://api.electricitymaps.com/v3/carbon-intensity/latest"

_IAM_ROLE_ARN_RE = re.compile(
    r"^arn:aws(?:-cn|-us-gov)?:iam::(\d{12}):role/[A-Za-z0-9+=,.@_\-/]+$"
)

# Maps AWS region identifiers to Electricity Maps / official grid balancing zones.
AWS_REGION_TO_GRID_ZONE: Dict[str, str] = {
    "us-east-1": "US-MIDA-PJM",
    "us-east-2": "US-MIDA-PJM",
    "us-west-1": "US-CAL-CISO",
    "us-west-2": "US-NW-PACW",
    "ca-central-1": "CA-QC",
    "eu-west-1": "IE",
    "eu-west-2": "GB",
    "eu-west-3": "FR",
    "eu-central-1": "DE",
    "eu-north-1": "SE",
    "eu-south-1": "IT",
    "ap-south-1": "IN-WE",
    "ap-northeast-1": "JP-TK",
    "ap-southeast-1": "SG",
    "ap-southeast-2": "AU-NSW",
    "sa-east-1": "BR-CS",
    "me-central-1": "AE",
    "me-south-1": "BH",
    "af-south-1": "ZA",
}

# Verified Ember 2024 / Our World in Data & EPA eGRID carbon intensity table (gCO2eq/kWh).
REGION_CARBON_FALLBACK: Dict[str, float] = {
    "us-east-1": 383.78,       # United States (Ember 2024 / PJM)
    "us-east-2": 383.78,       # United States (Ember 2024 / PJM)
    "us-west-1": 215.0,        # California CAISO (EPA eGRID / Ember)
    "us-west-2": 215.0,        # US Northwest BPAT/NWPP (EPA eGRID)
    "ca-central-1": 185.35,    # Canada (Ember 2024)
    "eu-west-1": 270.91,       # Ireland (Ember 2024)
    "eu-west-2": 216.5,        # United Kingdom (Ember 2024)
    "eu-west-3": 40.48,        # France (Ember 2024)
    "eu-central-1": 336.38,    # Germany (Ember 2024)
    "eu-north-1": 34.91,       # Sweden (Ember 2024)
    "eu-south-1": 281.4,       # Italy (Ember 2024)
    "ap-south-1": 705.4,       # India (Ember 2024)
    "ap-northeast-1": 483.43,  # Japan (Ember 2024)
    "ap-southeast-1": 498.74,  # Singapore (Ember 2024)
    "ap-southeast-2": 553.83,  # Australia (Ember 2024)
    "sa-east-1": 106.06,       # Brazil (Ember 2024)
    "me-central-1": 467.51,    # United Arab Emirates (Ember 2024)
    "me-south-1": 902.24,      # Bahrain (Ember 2024)
    "af-south-1": 717.36,      # South Africa (Ember 2024)
}

REGION_CARBON_CITATIONS: Dict[str, str] = {
    region: "Ember Yearly Electricity Data 2024 (via Our World in Data) / EPA eGRID"
    for region in REGION_CARBON_FALLBACK
}


@dataclass
class AWSAccount:
    """Linked AWS account metadata (never contains raw credentials)."""
    account_id: str
    role_arn: str
    region: str
    account_name: str
    created_at: str
    access_level: str = "read-only"
    status: str = "ACTIVE"


@dataclass
class AWSHealthStatus:
    """Health and readiness status of the AWS integration."""
    status: str
    connected_accounts: int
    regions: List[str]
    last_updated: str


class AWSSTSError(Exception):
    """Raised when AWS STS AssumeRole or cross-account verification fails."""

    def __init__(
        self,
        message: str,
        error_code: str = "UNKNOWN",
        account_id: Optional[str] = None,
        response: Optional[str] = None,
    ):
        super().__init__(message)
        self.error_code = error_code
        self.account_id = account_id
        self.response = response


def validate_account_and_role_arn(account_id: str, role_arn: str) -> None:
    """Validate 12-digit AWS account ID and verify that the IAM Role ARN belongs to the same account."""
    clean_acct = (account_id or "").strip()
    if not clean_acct.isdigit() or len(clean_acct) != 12:
        raise ValueError(f"Invalid AWS account ID: '{account_id}'. Must be exactly 12 digits.")

    clean_arn = (role_arn or "").strip()
    m = _IAM_ROLE_ARN_RE.match(clean_arn)
    if not m:
        raise ValueError(
            f"Invalid IAM Role ARN: '{role_arn}'. Expected format 'arn:aws:iam::<12-digit-account-id>:role/<role-name>'."
        )
    arn_account_id = m.group(1)
    if arn_account_id != clean_acct:
        raise ValueError(
            f"Account ID mismatch: account_id is '{clean_acct}' but role_arn belongs to account '{arn_account_id}'."
        )


def assume_role(
    account_id: str,
    role_arn: str,
    session_name: Optional[str] = None,
    external_id: Optional[str] = None,
    region: str = "us-east-1",
    sts_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Assume an IAM role in a target AWS account and return temporary credentials for internal SDK calls."""
    validate_account_and_role_arn(account_id, role_arn)

    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    unique_session = session_name or f"greencode-auditor-{uuid.uuid4().hex[:10]}"
    try:
        client = sts_client or boto3.client("sts", region_name=region)
        params: Dict[str, Any] = {
            "RoleArn": role_arn.strip(),
            "RoleSessionName": unique_session[:64],
            "DurationSeconds": 3600,
        }
        if external_id:
            params["ExternalId"] = external_id.strip()

        response = client.assume_role(**params)
        creds = response.get("Credentials") or {}
        if not creds.get("AccessKeyId") or not creds.get("SecretAccessKey"):
            raise AWSSTSError(
                "STS AssumeRole returned incomplete credentials.",
                error_code="INCOMPLETE_CREDENTIALS",
                account_id=account_id,
            )

        assumed_arn = (response.get("AssumedRoleUser") or {}).get("Arn", "")
        if assumed_arn and account_id not in assumed_arn:
            raise AWSSTSError(
                f"AssumedRoleUser ARN '{assumed_arn}' does not match target account '{account_id}'.",
                error_code="ACCOUNT_MISMATCH",
                account_id=account_id,
            )

        # Verify caller identity of the assumed session matches the target 12-digit account ID
        verified_caller_account = account_id.strip()
        if sts_client is not None:
            if hasattr(sts_client, "get_caller_identity"):
                identity = sts_client.get_caller_identity() or {}
                caller_acct = str(identity.get("Account") or "").strip()
                if caller_acct and caller_acct != account_id.strip():
                    raise AWSSTSError(
                        f"STS get_caller_identity Account '{caller_acct}' does not match '{account_id}'.",
                        error_code="CALLER_IDENTITY_MISMATCH",
                        account_id=account_id,
                    )
        else:
            assumed_sts = boto3.client(
                "sts",
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds.get("SessionToken", ""),
                region_name=region,
            )
            identity = assumed_sts.get_caller_identity() or {}
            caller_acct = str(identity.get("Account") or "").strip()
            if caller_acct and caller_acct != account_id.strip():
                raise AWSSTSError(
                    f"STS get_caller_identity Account '{caller_acct}' does not match '{account_id}'.",
                    error_code="CALLER_IDENTITY_MISMATCH",
                    account_id=account_id,
                )
            verified_caller_account = caller_acct or verified_caller_account

        expiration = creds.get("Expiration")
        exp_iso = expiration.isoformat() if hasattr(expiration, "isoformat") else str(expiration or "")

        return {
            "status": "SUCCESS",
            "access_key_id": creds["AccessKeyId"],
            "secret_access_key": creds["SecretAccessKey"],
            "session_token": creds.get("SessionToken", ""),
            "expiration": exp_iso,
            "session_name": unique_session[:64],
            "account_id": verified_caller_account,
            "role_arn": role_arn.strip(),
            "source": "aws_sts_assume_role",
            "method": "sts_assume_role",
            "tier": "live",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "Unknown")
        raise AWSSTSError(
            f"STS AssumeRole failed: {error_code}",
            error_code=error_code,
            account_id=account_id,
            response=str(exc),
        )
    except BotoCoreError as exc:
        raise AWSSTSError(
            f"STS AssumeRole transport/credentials error: {type(exc).__name__}",
            error_code=type(exc).__name__,
            account_id=account_id,
            response=str(exc),
        )


def list_available_regions() -> List[str]:
    """Return the sorted list of AWS regions supported for carbon and FinOps monitoring."""
    return sorted(REGION_CARBON_FALLBACK.keys())


def get_region_carbon_intensity(
    region: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve grid carbon intensity (gCO2eq/kWh) for an AWS region.

    Maps the AWS region identifier (e.g. `us-east-1`, `eu-central-1`) to its
    corresponding electricity grid balancing zone (`US-MIDA-PJM`, `DE`),
    queries live Electricity Maps or Tier-1 grid providers first with a strict
    timeout, and falls back to the cited Ember 2024 reference table.
    """
    region_clean = (region or "us-east-1").strip().lower()
    grid_zone = AWS_REGION_TO_GRID_ZONE.get(region_clean, region_clean.upper())
    em_key = (
        api_key
        or os.environ.get("GREENCODE_ELECTRICITY_MAPS_KEY")
        or os.environ.get("ELECTRICITY_MAPS_API_KEY")
        or ""
    ).strip()

    if em_key:
        try:
            response = requests.get(
                ELECTRICITY_MAPS_REGIONAL_URL,
                params={"zone": grid_zone},
                headers={"auth-token": em_key},
                timeout=6.0,
            )
            if response.status_code == 200:
                data = response.json()
                val = data.get("carbonIntensity")
                if val is None:
                    val = data.get("intensity")
                if val is not None:
                    return {
                        "region": region_clean,
                        "grid_zone": grid_zone,
                        "carbon_intensity": float(val),
                        "unit": "gCO2eq/kWh",
                        "source": "electricity_maps_api",
                        "method": "live_grid_intensity",
                        "tier": "live",
                        "citation": f"Electricity Maps API v3 (zone={grid_zone})",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
        except Exception as exc:
            logger.warning("Electricity Maps request failed for %s (zone %s): %s", region_clean, grid_zone, exc)

    # Also consult the multi-provider Tier-1 resolver (UK ESO, US EIA-930, ENTSO-E)
    try:
        resolved = carbon_intensity.resolve_carbon_intensity(zone=grid_zone, use_cache=True)
        if resolved.is_live and resolved.carbon_intensity > 0:
            return {
                "region": region_clean,
                "grid_zone": grid_zone,
                "carbon_intensity": float(resolved.carbon_intensity),
                "unit": "gCO2eq/kWh",
                "source": resolved.intensity_source,
                "method": "live_grid_intensity",
                "tier": "live",
                "citation": resolved.citation,
                "timestamp": resolved.observed_at,
            }
    except Exception:
        pass  # no-op: proceed to Ember 2024 static reference table

    intensity = REGION_CARBON_FALLBACK.get(region_clean, 383.78)
    citation = REGION_CARBON_CITATIONS.get(
        region_clean,
        "Ember Yearly Electricity Data 2024 (via Our World in Data)",
    )
    return {
        "region": region_clean,
        "grid_zone": grid_zone,
        "carbon_intensity": intensity,
        "unit": "gCO2eq/kWh",
        "source": "ember_2024_reference_table",
        "method": "annual_grid_average_reference",
        "tier": "model",
        "citation": citation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_cost_and_usage(
    region: str,
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    granularity: str = "MONTHLY",
    role_arn: Optional[str] = None,
    external_id: Optional[str] = None,
    sts_client: Optional[Any] = None,
    budgets_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Fetch month-to-date AWS cost data for a linked AWS account using STS AssumeRole credentials."""
    clean_acct = (account_id or "").strip()
    if not clean_acct.isdigit() or len(clean_acct) != 12:
        raise ValueError(f"Invalid AWS account ID: '{account_id}'. Must be 12 digits.")

    now_utc = datetime.now(timezone.utc)
    effective_start = start_date or now_utc.strftime("%Y-%m-01")
    effective_end = end_date or now_utc.strftime("%Y-%m-%d")

    resolved_role_arn = role_arn
    resolved_external_id = external_id
    if not resolved_role_arn:
        from app.database import get_aws_account
        linked = get_aws_account(clean_acct)
        if linked:
            resolved_role_arn = linked.role_arn
            resolved_external_id = resolved_external_id or linked.external_id

    if not resolved_role_arn:
        raise AWSSTSError(
            f"Account {clean_acct} is not linked or missing an IAM Role ARN for STS AssumeRole.",
            error_code="ACCOUNT_NOT_LINKED",
            account_id=clean_acct,
        )

    # Always obtain temporary credentials scoped to the target linked account via AssumeRole
    creds = assume_role(
        account_id=clean_acct,
        role_arn=resolved_role_arn,
        external_id=resolved_external_id,
        region=region,
        sts_client=sts_client,
    )

    import boto3
    from botocore.exceptions import BotoCoreError, ClientError

    try:
        b_client = budgets_client or boto3.client(
            "budgets",
            aws_access_key_id=creds["access_key_id"],
            aws_secret_access_key=creds["secret_access_key"],
            aws_session_token=creds["session_token"],
            region_name=region,
        )

        response = b_client.describe_budgets(AccountId=clean_acct)
        actual_spend = 0.0
        forecasted_spend = 0.0
        budgets_list = response.get("Budgets") or []
        for budget in budgets_list:
            calc = budget.get("CalculatedSpend") or {}
            actual = calc.get("ActualSpend") or {}
            forecast = calc.get("ForecastedSpend") or {}
            actual_spend += float(actual.get("Amount") or 0.0)
            forecasted_spend += float(forecast.get("Amount") or 0.0)

        return {
            "account_id": clean_acct,
            "region": region,
            "start_date": effective_start,
            "end_date": effective_end,
            "granularity": granularity,
            "actual_spend_usd": round(actual_spend, 2),
            "forecasted_spend_usd": round(forecasted_spend, 2),
            "budgets_evaluated": len(budgets_list),
            "currency": "USD",
            "source": "aws_budgets_api",
            "method": "sts_assumed_role_describe_budgets",
            "tier": "live",
            "timestamp": now_utc.isoformat(),
        }
    except (ClientError, BotoCoreError) as exc:
        error_code = (
            exc.response.get("Error", {}).get("Code", "Unknown")
            if isinstance(exc, ClientError)
            else type(exc).__name__
        )
        return {
            "account_id": clean_acct,
            "region": region,
            "start_date": effective_start,
            "end_date": effective_end,
            "actual_spend_usd": 0.0,
            "forecasted_spend_usd": 0.0,
            "error": f"AWS Budgets API error: {error_code}",
            "source": "aws_budgets_api_unavailable",
            "method": "fail_closed",
            "tier": "unavailable",
            "timestamp": now_utc.isoformat(),
        }


def get_aws_cost_carbon_data(
    region: str,
    account_id: str,
    role_arn: Optional[str] = None,
    sts_client: Optional[Any] = None,
    budgets_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compute month-to-date AWS cost and physics-calibrated carbon footprint for a linked account.

    Replaces arbitrary dollar-times-intensity formulas with `CalibratedEnergyModel`:
    1. Converts actual EC2/compute spend (`actual_spend_usd`) into equivalent active
       `c6g.xlarge` (4 vCPU) compute hours using AWS's published on-demand rate ($0.136/hr).
    2. Calculates PUE-adjusted energy consumption (`estimated_energy_kwh`) via
       `CalibratedEnergyModel.calculate_energy`.
    3. Multiplies `estimated_energy_kwh * (carbon_intensity_g_per_kwh / 1000)` to yield
       physically dimensional `estimated_co2e_kg`.
    """
    now_utc = datetime.now(timezone.utc)
    mtd_start = now_utc.strftime("%Y-%m-01")
    mtd_end = now_utc.strftime("%Y-%m-%d")

    carbon = get_region_carbon_intensity(region)
    cost = get_cost_and_usage(
        region=region,
        account_id=account_id,
        start_date=mtd_start,
        end_date=mtd_end,
        role_arn=role_arn,
        sts_client=sts_client,
        budgets_client=budgets_client,
    )

    spend_usd = float(cost.get("actual_spend_usd") or 0.0)
    intensity_g_kwh = float(carbon.get("carbon_intensity") or 383.78)

    # AWS c6g.xlarge (4 vCPU, 8 GB) on-demand rate is $0.136/hour ($0.034/vCPU-hour)
    reference_hourly_rate_usd = 0.136
    if spend_usd > 0.0:
        equivalent_instance_hours = spend_usd / reference_hourly_rate_usd
        calibrated = CalibratedEnergyModel.calculate_energy(
            duration_seconds=equivalent_instance_hours * 3600.0,
            cpu_utilization_pct=45.0,
            memory_mb=8192.0,
            cloud_instance="c6g.xlarge",
        )
        estimated_energy_kwh = round(calibrated.energy_kwh, 4)
        estimated_co2e_kg = round(estimated_energy_kwh * (intensity_g_kwh / 1000.0), 4)
    else:
        estimated_energy_kwh = 0.0
        estimated_co2e_kg = 0.0

    return {
        "region": region,
        "grid_zone": carbon.get("grid_zone"),
        "account_id": account_id,
        "period_start": mtd_start,
        "period_end": mtd_end,
        "carbon_intensity_gco2_kwh": intensity_g_kwh,
        "carbon_source": carbon.get("source"),
        "carbon_tier": carbon.get("tier"),
        "cost_usd": spend_usd,
        "cost_source": cost.get("source"),
        "cost_tier": cost.get("tier"),
        "estimated_energy_kwh": estimated_energy_kwh,
        "estimated_co2e_kg": estimated_co2e_kg,
        "timestamp": now_utc.isoformat(),
        "provenance": {
            "carbon": {
                "source": carbon.get("source"),
                "method": carbon.get("method"),
                "tier": carbon.get("tier"),
                "citation": carbon.get("citation"),
            },
            "cost": {
                "source": cost.get("source"),
                "method": cost.get("method"),
                "tier": cost.get("tier"),
            },
            "energy_conversion_model": "CalibratedEnergyModel (c6g.xlarge @ $0.136/hr on-demand baseline, PUE=1.15)",
        },
    }


def link_aws_account(
    account_id: str,
    role_arn: str,
    region: str = "us-east-1",
    account_name: str = "AWS Account",
    external_id: Optional[str] = None,
    org_id: int = 1,
    sts_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Validate and link an AWS account via STS AssumeRole, persisting metadata to SQLite/Postgres.

    Never exposes temporary STS credentials (`access_key_id`, `secret_access_key`, `session_token`)
    in the returned response or database record.
    """
    validate_account_and_role_arn(account_id, role_arn)

    try:
        creds = assume_role(
            account_id=account_id.strip(),
            role_arn=role_arn.strip(),
            external_id=external_id,
            region=region,
            sts_client=sts_client,
        )

        from app.database import create_aws_account

        db_account = create_aws_account(
            account_id=account_id.strip(),
            role_arn=role_arn.strip(),
            region=region,
            account_name=account_name,
            external_id=external_id,
            status="ACTIVE",
            access_level="read-only",
            org_id=org_id,
        )

        return {
            "status": "LINKED",
            "account_id": db_account.account_id,
            "account_name": db_account.account_name,
            "region": db_account.region,
            "role_arn": db_account.role_arn,
            "linked_at": db_account.linked_at.isoformat() if db_account.linked_at else creds["timestamp"],
            "access_level": db_account.access_level,
            "sts_session_verified": True,
            "source": "aws_sts_assume_role",
        }
    except AWSSTSError as exc:
        return {
            "status": "LINK_FAILED",
            "account_id": account_id.strip(),
            "error": str(exc),
            "error_code": exc.error_code,
            "source": "aws_sts_assume_role",
            "tier": "live",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def list_linked_accounts(org_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """List all AWS accounts linked in the database."""
    from app.database import get_all_aws_accounts

    accounts = get_all_aws_accounts(org_id=org_id)
    return [
        {
            "account_id": acc.account_id,
            "account_name": acc.account_name,
            "region": acc.region,
            "role_arn": acc.role_arn,
            "status": acc.status,
            "linked_at": acc.linked_at.isoformat() if acc.linked_at else None,
            "access_level": acc.access_level,
            "org_id": acc.org_id,
        }
        for acc in accounts
    ]


def delete_aws_account(account_id: str, org_id: Optional[int] = None) -> bool:
    """Unlink an AWS account from GreenCode."""
    from app.database import delete_aws_account_record

    return delete_aws_account_record(account_id=account_id, org_id=org_id)


def get_aws_health_status(org_id: Optional[int] = None) -> Dict[str, Any]:
    """Return health and connected-account summary for the AWS integration."""
    accounts = list_linked_accounts(org_id=org_id)
    health = AWSHealthStatus(
        status="READY",
        connected_accounts=len(accounts),
        regions=list_available_regions(),
        last_updated=datetime.now(timezone.utc).isoformat(),
    )
    return asdict(health)

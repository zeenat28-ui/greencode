"""AWS Account Linking, STS AssumeRole, Regional Carbon Intensity, and Cost-Carbon Router."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app import amazon_service
from app.auth.dependencies import get_current_actor, require_permission
from app.auth.roles import Permission, Role, normalize_role

router = APIRouter(prefix="/api/aws", tags=["Amazon Web Services (AWS) FinOps & Carbon"])


def _enforce_tenant(actor: Dict[str, Any], org_id: int) -> None:
    """Refuse cross-tenant access unless the caller is a platform superadmin."""
    role = normalize_role(actor.get("role"))
    if role != Role.SUPERADMIN and actor.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Tenant isolation violation: token belongs to organization "
                f"{actor.get('org_id')} but requested organization {org_id}"
            ),
        )


class LinkAWSAccountRequest(BaseModel):
    org_id: int = 1
    account_id: str = Field(..., min_length=12, max_length=12)
    role_arn: str = Field(..., min_length=20)
    region: str = "us-east-1"
    account_name: str = "AWS Account"
    external_id: Optional[str] = None


@router.get("/health")
async def aws_integration_health(
    org_id: int = Query(1),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Return AWS integration health, connected accounts count, and supported regions."""
    _enforce_tenant(actor, org_id)
    return amazon_service.get_aws_health_status(org_id=org_id)


@router.get("/regions")
async def get_supported_aws_regions():
    """List AWS regions supported for carbon intensity and FinOps monitoring."""
    return {
        "regions": amazon_service.list_available_regions(),
        "region_to_grid_zone": dict(amazon_service.AWS_REGION_TO_GRID_ZONE),
    }


@router.get("/regions/{region}/carbon-intensity")
async def get_aws_region_carbon_intensity(region: str):
    """Resolve live or Ember-2024 reference carbon intensity (gCO2eq/kWh) for an AWS region."""
    return amazon_service.get_region_carbon_intensity(region=region)


@router.get("/regions/recommend-migration")
async def recommend_aws_region_migration(
    current_region: str = Query("us-east-1"),
    monthly_kwh: float = Query(1000.0, ge=0.0),
    data_residency: str = Query("GLOBAL"),
    max_candidates: int = Query(5, ge=1, le=20),
):
    """Recommend carbon-optimal AWS target regions respecting data residency and latency partitions."""
    return amazon_service.recommend_optimal_aws_region(
        current_region=current_region,
        monthly_kwh=monthly_kwh,
        data_residency=data_residency,
        max_candidates=max_candidates,
    )


@router.post("/accounts/link", status_code=status.HTTP_200_OK)
async def link_aws_account_endpoint(
    payload: LinkAWSAccountRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Validate and link an AWS account via STS AssumeRole."""
    _enforce_tenant(actor, payload.org_id)
    try:
        return amazon_service.link_aws_account(
            account_id=payload.account_id,
            role_arn=payload.role_arn,
            region=payload.region,
            account_name=payload.account_name,
            external_id=payload.external_id,
            org_id=payload.org_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/accounts")
async def list_linked_aws_accounts(
    org_id: int = Query(1),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """List all AWS accounts linked to the organization."""
    _enforce_tenant(actor, org_id)
    return {"accounts": amazon_service.list_linked_accounts(org_id=org_id)}


@router.delete("/accounts/{account_id}")
async def unlink_aws_account(
    account_id: str,
    org_id: int = Query(1),
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Unlink an AWS account from the organization."""
    _enforce_tenant(actor, org_id)
    removed = amazon_service.delete_aws_account(account_id=account_id, org_id=org_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AWS account {account_id} not found for organization {org_id}.",
        )
    return {"deleted": True, "account_id": account_id, "org_id": org_id}


@router.get("/accounts/{account_id}/cost-carbon")
async def get_account_cost_carbon(
    account_id: str,
    region: str = Query("us-east-1"),
    org_id: int = Query(1),
    instance_type: str = Query("c6g.xlarge"),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Fetch month-to-date AWS Budgets spend and physics-calibrated carbon footprint for a linked account."""
    _enforce_tenant(actor, org_id)
    try:
        return amazon_service.get_aws_cost_carbon_data(
            region=region,
            account_id=account_id,
            org_id=org_id,
            instance_type=instance_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except amazon_service.AWSSTSError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


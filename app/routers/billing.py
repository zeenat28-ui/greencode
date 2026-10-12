"""Enterprise Billing REST API Router."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.services.billing_service import BillingService
from app.auth.dependencies import get_current_actor, require_permission
from app.auth.roles import Permission

router = APIRouter(prefix="/api/billing", tags=["Billing"])


def _enforce_tenant(actor: Dict[str, Any], org_id: int) -> None:
    """Refuse cross-tenant billing access for any org_id mismatch."""
    if actor.get("org_id") != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Tenant isolation violation: token belongs to organization "
                f"{actor.get('org_id')} but requested organization {org_id}"
            ),
        )


class CreateSubscriptionRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    tier: str = Field("free", pattern="^(free|pro|enterprise)$")
    seats: int = Field(1, ge=1)
    status: str = Field(
        "active",
        pattern="^(active|trialing|past_due|canceled)$",
    )


class ChangeTierRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    new_tier: str = Field(..., pattern="^(free|pro|enterprise)$")
    seats: Optional[int] = Field(None, ge=1)


class SetSeatsRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    seats: int = Field(..., ge=1)


class GenerateInvoiceRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    period: Optional[str] = None


class ListInvoicesRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    limit: int = Field(24, ge=1, le=1000)


@router.post(
    "/subscription",
    status_code=status.HTTP_201_CREATED,
)
async def upsert_subscription(
    payload: CreateSubscriptionRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Create or update the tenant's billing subscription."""
    _enforce_tenant(actor, payload.org_id)
    return BillingService.create_subscription(
        org_id=payload.org_id,
        tier=payload.tier,
        seats=payload.seats,
        status=payload.status,
    )


@router.post("/tier", status_code=status.HTTP_200_OK)
async def change_tier(
    payload: ChangeTierRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Upgrade or downgrade the tenant's plan."""
    _enforce_tenant(actor, payload.org_id)
    return BillingService.change_tier(
        org_id=payload.org_id,
        new_tier=payload.new_tier,
        seats=payload.seats,
    )


@router.post("/seats", status_code=status.HTTP_200_OK)
async def set_seats(
    payload: SetSeatsRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Adjust the seat count on the tenant's subscription."""
    _enforce_tenant(actor, payload.org_id)
    return BillingService.set_seats(org_id=payload.org_id, seats=payload.seats)


@router.post(
    "/invoice",
    status_code=status.HTTP_201_CREATED,
)
async def generate_invoice(
    payload: GenerateInvoiceRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Generate (or regenerate) an invoice for a billing period."""
    _enforce_tenant(actor, payload.org_id)
    return BillingService.generate_invoice(org_id=payload.org_id, period=payload.period)


@router.get("/usage", status_code=status.HTTP_200_OK)
async def get_usage_snapshot(
    org_id: int = Query(1, gt=0),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Live usage vs quota for the customer dashboard + billing controls (GET)."""
    _enforce_tenant(actor, org_id)
    return BillingService.usage_snapshot(org_id=org_id)


@router.post("/usage", status_code=status.HTTP_200_OK)
async def usage_snapshot(
    payload: GenerateInvoiceRequest,
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Live usage vs quota for the customer dashboard + billing controls."""
    _enforce_tenant(actor, payload.org_id)
    return BillingService.usage_snapshot(org_id=payload.org_id)


@router.get("/invoices", status_code=status.HTTP_200_OK)
async def list_invoices(
    org_id: int = Query(..., gt=0),
    limit: int = Query(24, ge=1, le=1000),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """List the tenant's invoice history (newest first)."""
    _enforce_tenant(actor, org_id)
    return BillingService.list_invoices(org_id=org_id, limit=limit)


@router.get(
    "/invoice/{invoice_number}",
    status_code=status.HTTP_200_OK,
)
async def get_invoice(
    invoice_number: str,
    org_id: int = Query(..., gt=0),
    actor: Dict[str, Any] = Depends(get_current_actor),
):
    """Retrieve a single invoice by number."""
    _enforce_tenant(actor, org_id)
    return BillingService.get_invoice(org_id=org_id, invoice_number=invoice_number)


@router.post(
    "/invoice/{invoice_number}/pay",
    status_code=status.HTTP_200_OK,
)
async def mark_invoice_paid(
    invoice_number: str,
    org_id: int = Query(..., gt=0),
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Mark an invoice as paid."""
    _enforce_tenant(actor, org_id)
    return BillingService.mark_invoice_paid(org_id=org_id, invoice_number=invoice_number)


class IssueLicenseRequest(BaseModel):
    org_id: int = Field(..., gt=0)
    tier: str = Field("pro", pattern="^(free|pro|enterprise)$")
    seats: int = Field(5, ge=1, le=10000)
    expires_days: int = Field(365, ge=1, le=3650)


class ActivateLicenseRequest(BaseModel):
    org_id: int = Field(1, gt=0)
    license_key: str = Field(..., min_length=12, max_length=512)


class OpenCollectiveWebhookPayload(BaseModel):
    type: str = Field("order.processed", max_length=120)
    org_id: int = Field(1, gt=0)
    amount_usd: float = Field(..., ge=0.0)
    sponsor_slug: str = Field("contributor", max_length=200)
    seats: int = Field(5, ge=1, le=10000)


@router.post("/license/issue", status_code=status.HTTP_200_OK)
async def issue_license_key(
    payload: IssueLicenseRequest,
    actor: Dict[str, Any] = Depends(require_permission(Permission.MANAGE_ORG)),
):
    """Issue a cryptographically signed GC-LIC-... commercial license key for the organization."""
    _enforce_tenant(actor, payload.org_id)
    from app.pricing import LicenseKeyManager
    key = LicenseKeyManager.generate_license_key(
        org_id=payload.org_id,
        tier=payload.tier,
        seats=payload.seats,
        expires_days=payload.expires_days,
    )
    verification = LicenseKeyManager.verify_license_key(key)
    return {
        "status": "issued",
        "license_key": key,
        "org_id": payload.org_id,
        "tier": payload.tier,
        "seats": payload.seats,
        "expires_at_unix": verification.get("expires_at_unix"),
    }


@router.post("/license/activate", status_code=status.HTTP_200_OK)
async def activate_license_key(
    payload: ActivateLicenseRequest,
):
    """Verify a signed GC-LIC-... license key and activate the corresponding subscription tier."""
    from app.pricing import LicenseKeyManager
    verification = LicenseKeyManager.verify_license_key(payload.license_key)
    if not verification.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=verification.get("error", "Invalid license key."),
        )
    if int(verification["org_id"]) != int(payload.org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"License key was issued for organization #{verification['org_id']}, not #{payload.org_id}.",
        )
    sub = BillingService.change_tier(
        org_id=payload.org_id,
        new_tier=verification["tier"],
        seats=verification["seats"],
    )
    return {
        "status": "activated",
        "subscription": sub,
        "license": verification,
    }


@router.post("/webhooks/opencollective", status_code=status.HTTP_200_OK)
async def handle_opencollective_webhook(
    payload: OpenCollectiveWebhookPayload,
):
    """Process an Open Collective / GitHub Sponsors contribution and auto-provision the matching tier."""
    from app.pricing import LicenseKeyManager
    if payload.amount_usd >= 499.0:
        assigned_tier = "enterprise"
        seats = max(payload.seats, 25)
    elif payload.amount_usd >= 49.0:
        assigned_tier = "pro"
        seats = max(payload.seats, 5)
    else:
        assigned_tier = "free"
        seats = 1

    sub = BillingService.change_tier(
        org_id=payload.org_id,
        new_tier=assigned_tier,
        seats=seats,
    )
    license_key = LicenseKeyManager.generate_license_key(
        org_id=payload.org_id,
        tier=assigned_tier,
        seats=seats,
        expires_days=365,
    )
    return {
        "status": "processed",
        "event_type": payload.type,
        "sponsor_slug": payload.sponsor_slug,
        "amount_usd": payload.amount_usd,
        "assigned_tier": assigned_tier,
        "subscription": sub,
        "license_key": license_key,
    }


@router.get("/focus/sample-report", status_code=status.HTTP_200_OK)
async def get_focus_sample_reconciliation():
    """Return a live FinOps Foundation FOCUS 1.4 cloud billing and Scope 2/3 carbon reconciliation report."""
    from app.finops_focus import reconcile_focus_billing

    return reconcile_focus_billing()


@router.post("/focus/reconcile", status_code=status.HTTP_200_OK)
async def reconcile_focus_cloud_billing(payload: Dict[str, Any]):
    """Ingest FinOps Foundation FOCUS 1.4 JSON rows or CSV text and reconcile spend with kWh and kg CO2e."""
    from app.finops_focus import reconcile_focus_billing

    rows = payload.get("rows")
    csv_text = payload.get("csv_text")
    return reconcile_focus_billing(
        rows=rows if isinstance(rows, list) else None,
        csv_text=str(csv_text) if csv_text else None,
    )


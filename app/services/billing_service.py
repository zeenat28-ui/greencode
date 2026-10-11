"""Enterprise Billing Service: subscription lifecycle + invoice generation.

Turns the previously static pricing catalog into real, durable billing state:
each tenant has exactly one ``Subscription`` (one row per org) and a history of
generated ``Invoice`` rows. Invoice totals are derived from the tier base price
plus a metered overage priced against usage that exceeded the plan's included
call allowance (using the real ``usage_events`` ledger).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.database import (
    AuditLog,
    Invoice,
    SessionLocal,
    Subscription,
)
from app.pricing import PRICING_CATALOG, PricingManager
from app.services.usage_service import UsageService

logger = logging.getLogger("greencode.services.billing")

# Dollars per call beyond the plan's included allowance.
OVERAGE_USD_PER_CALL = 0.002


class BillingService:
    """Manages tenant subscriptions and generates usage-based invoices."""

    # ------------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------------
    @classmethod
    def get_subscription(cls, org_id: int) -> Optional[Dict[str, Any]]:
        db: Session = SessionLocal()
        try:
            sub = (
                db.query(Subscription)
                .filter(Subscription.org_id == org_id)
                .one_or_none()
            )
            return cls._sub_to_dict(sub) if sub else None
        finally:
            db.close()

    @classmethod
    def ensure_subscription(cls, org_id: int, tier: str = "free") -> Dict[str, Any]:
        """Return the tenant's subscription, creating a free one if absent."""
        existing = cls.get_subscription(org_id)
        if existing:
            return existing
        return cls.create_subscription(org_id=org_id, tier=tier)

    @classmethod
    def create_subscription(
        cls,
        org_id: int,
        tier: str = "free",
        seats: int = 1,
        status: str = "active",
    ) -> Dict[str, Any]:
        clean_tier = tier.lower().strip()
        if clean_tier not in PRICING_CATALOG:
            raise KeyError(f"Unknown pricing tier: {tier}")
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        db: Session = SessionLocal()
        try:
            sub = Subscription(
                org_id=org_id,
                tier=clean_tier,
                status=status,
                seats=seats,
                current_period_start=now,
                current_period_end=period_end,
            )
            db.add(sub)
            db.commit()
            db.refresh(sub)
            result = cls._sub_to_dict(sub)
            cls._audit(org_id, "subscription:create", str(sub.id), f"tier={clean_tier}")
            return result
        finally:
            db.close()

    @classmethod
    def change_tier(
        cls,
        org_id: int,
        new_tier: str,
        seats: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Upgrade/downgrade a tenant's plan (moves to a fresh billing period)."""
        new_tier = new_tier.lower().strip()
        if new_tier not in PRICING_CATALOG:
            raise KeyError(f"Unknown pricing tier: {new_tier}")
        PricingManager.get_tier(new_tier)
        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)
        db: Session = SessionLocal()
        try:
            sub = (
                db.query(Subscription)
                .filter(Subscription.org_id == org_id)
                .one_or_none()
            )
            if not sub:
                sub = Subscription(org_id=org_id, tier=new_tier, current_period_start=now, current_period_end=period_end)
                db.add(sub)
            sub.tier = new_tier
            sub.status = "active"
            sub.current_period_start = now
            sub.current_period_end = period_end
            if seats is not None:
                sub.seats = seats
            db.commit()
            db.refresh(sub)
            result = cls._sub_to_dict(sub)
            cls._audit(org_id, "subscription:change_tier", str(sub.id), f"tier={new_tier}")
            return result
        finally:
            db.close()

    @classmethod
    def set_seats(cls, org_id: int, seats: int) -> Dict[str, Any]:
        if seats < 1:
            raise ValueError("seats must be >= 1")
        db: Session = SessionLocal()
        try:
            sub = db.query(Subscription).filter(Subscription.org_id == org_id).one_or_none()
            if not sub:
                raise ValueError(f"No subscription for org {org_id}")
            sub.seats = seats
            db.commit()
            db.refresh(sub)
            result = cls._sub_to_dict(sub)
            cls._audit(org_id, "subscription:set_seats", str(sub.id), f"seats={seats}")
            return result
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Invoice generation
    # ------------------------------------------------------------------
    @classmethod
    def generate_invoice(
        cls,
        org_id: int,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an invoice for the current/selected billing period.

        total = base subscription price + overage for calls beyond the plan's
        included monthly allowance. Usage is read from the real ledger.
        """
        period = period or datetime.now(timezone.utc).strftime("%Y-%m")
        sub = cls.ensure_subscription(org_id)
        tier = PricingManager.get_tier(sub["tier"])

        usage = UsageService.get_monthly_usage(org_id, period, event_type="api_call")
        included = tier.max_monthly_api_calls
        overage_calls = max(0, usage - included)
        overage_usd = round(overage_calls * OVERAGE_USD_PER_CALL, 2)
        base_usd = round(tier.price_usd_monthly, 2)
        total_usd = round(base_usd + overage_usd, 2)

        line_items = [
            {"description": f"{tier.name} plan (base)", "amount_usd": base_usd},
            {
                "description": (
                    f"Overage: {overage_calls} calls beyond {included} included"
                ),
                "amount_usd": overage_usd,
            },
        ]

        invoice_number = cls._invoice_number(org_id, period)
        db: Session = SessionLocal()
        try:
            invoice = Invoice(
                org_id=org_id,
                invoice_number=invoice_number,
                period_year_month=period,
                status="open",
                base_amount_usd=base_usd,
                usage_overage_usd=overage_usd,
                total_amount_usd=total_usd,
                currency="USD",
                line_items_json=json.dumps(line_items),
            )
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
            result = cls._invoice_to_dict(invoice)
            cls._audit(org_id, "invoice:generate", invoice_number, f"total={total_usd}")
            return result
        finally:
            db.close()

    @classmethod
    def get_invoice(cls, org_id: int, invoice_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single invoice for an org (or None)."""
        db: Session = SessionLocal()
        try:
            inv = (
                db.query(Invoice)
                .filter(
                    Invoice.org_id == org_id,
                    Invoice.invoice_number == invoice_number,
                )
                .one_or_none()
            )
            return cls._invoice_to_dict(inv) if inv else None
        finally:
            db.close()

    @classmethod
    def mark_invoice_paid(cls, org_id: int, invoice_number: str) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            inv = (
                db.query(Invoice)
                .filter(
                    Invoice.org_id == org_id,
                    Invoice.invoice_number == invoice_number,
                )
                .one_or_none()
            )
            if not inv:
                raise ValueError(f"Invoice {invoice_number} not found for org {org_id}")
            inv.status = "paid"
            db.commit()
            db.refresh(inv)
            result = cls._invoice_to_dict(inv)
            cls._audit(org_id, "invoice:paid", invoice_number, f"total={inv.total_amount_usd}")
            return result
        finally:
            db.close()

    @classmethod
    def consume(cls, org_id: int, tier: str, event_type: str = "api_call") -> Dict[str, Any]:
        """Record a metered action against the tenant's plan quota.

        Delegates to :class:`app.services.usage_service.UsageService.consume`
        and returns the quota status (allowed / usage / limit / remaining).
        """
        return UsageService.consume(org_id, tier, event_type=event_type)

    @classmethod
    def list_invoices(cls, org_id: int, limit: int = 24) -> list:
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(Invoice)
                .filter(Invoice.org_id == org_id)
                .order_by(Invoice.created_at.desc(), Invoice.id.desc())
                .limit(limit)
                .all()
            )
            return [cls._invoice_to_dict(r) for r in rows]
        finally:
            db.close()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @classmethod
    def _invoice_number(cls, org_id: int, period: str) -> str:
        # Deterministic-ish, unique per org+period; single batched query avoids N+1 loop round-trips.
        db: Session = SessionLocal()
        try:
            seq = int(db.query(Invoice.id).filter(Invoice.org_id == org_id).count()) + 1
            compact = period.replace("-", "")
            base_num = f"GC-{compact}-{seq:04d}"
            existing_rows = (
                db.query(Invoice.invoice_number)
                .filter(Invoice.invoice_number.like(f"{base_num}%"))
                .all()
            )
            existing_set = {row[0] for row in existing_rows}
            if base_num not in existing_set:
                return base_num
            candidate = f"{base_num}-O{org_id}"
            idx = 2
            while candidate in existing_set:
                candidate = f"{base_num}-O{org_id}-{idx}"
                idx += 1
            return candidate
        finally:
            db.close()

    @staticmethod
    def _audit(org_id: int, action: str, resource_id: str, details: str) -> None:
        try:
            from app.audit_logs import AuditLogManager
            AuditLogManager.record_event(
                org_id=org_id,
                action=action,
                resource_type="billing",
                resource_id=resource_id,
                status="SUCCESS",
                details={"summary": details},
            )
        except Exception:  # pragma: no cover
            pass  # no-op

    @staticmethod
    def _sub_to_dict(sub: Subscription) -> Dict[str, Any]:
        return {
            "id": sub.id,
            "org_id": sub.org_id,
            "tier": sub.tier,
            "status": sub.status,
            "seats": sub.seats,
            "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
            "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
            "cancel_at_period_end": sub.cancel_at_period_end,
        }

    @staticmethod
    def _invoice_to_dict(inv: Invoice) -> Dict[str, Any]:
        return {
            "id": inv.id,
            "org_id": inv.org_id,
            "invoice_number": inv.invoice_number,
            "period": inv.period_year_month,
            "status": inv.status,
            "base_amount_usd": inv.base_amount_usd,
            "usage_overage_usd": inv.usage_overage_usd,
            "total_amount_usd": inv.total_amount_usd,
            "currency": inv.currency,
            "line_items": json.loads(inv.line_items_json) if inv.line_items_json else [],
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }

    @classmethod
    def usage_snapshot(cls, org_id: int) -> Dict[str, Any]:
        """Live usage vs quota for the customer dashboard + billing controls."""
        sub = cls.ensure_subscription(org_id)
        quota = UsageService.check_quota(org_id, sub["tier"])
        breakdown = UsageService.usage_breakdown(org_id)
        return {
            "org_id": org_id,
            "subscription": sub,
            "quota": quota,
            "breakdown": breakdown,
            "plan": PricingManager.get_tier(sub["tier"]).__dict__,
        }

    @classmethod
    def sync_usage_to_aws_marketplace(
        cls,
        org_id: int,
        product_code: str,
        customer_identifier: str,
        dimension: str = "api_calls",
        period: Optional[str] = None,
        region_name: str = "us-east-1",
        metering_client: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Report tenant's database-backed metered usage to AWS Marketplace Metering Service (`BatchMeterUsage`).

        Fails closed when `product_code` / `customer_identifier` are missing or when
        AWS Marketplace credentials / endpoints are unreachable.
        """
        if not product_code or not product_code.strip():
            return {"metered": False, "reason": "AWS Marketplace product_code is required."}
        if not customer_identifier or not customer_identifier.strip():
            return {"metered": False, "reason": "AWS Marketplace customer_identifier is required."}

        quantity = int(UsageService.get_monthly_usage(org_id, period=period))
        now_utc = datetime.now(timezone.utc)
        usage_record = {
            "Timestamp": now_utc,
            "CustomerIdentifier": customer_identifier.strip(),
            "Dimension": dimension,
            "Quantity": max(0, quantity),
        }

        try:
            if metering_client is None:
                import boto3
                metering_client = boto3.client("meteringmarketplace", region_name=region_name)

            resp = metering_client.batch_meter_usage(
                UsageRecords=[usage_record],
                ProductCode=product_code.strip(),
            )
            results = resp.get("Results") or []
            unprocessed = resp.get("UnprocessedRecords") or []
            metered_ok = len(results) > 0 and len(unprocessed) == 0
            metering_record_id = results[0].get("MeteringRecordId") if results else None
            status_code = results[0].get("Status") if results else "UNPROCESSED"

            if metered_ok:
                cls._audit(
                    org_id,
                    "aws_marketplace:batch_meter_usage",
                    str(metering_record_id or product_code),
                    f"dimension={dimension} quantity={quantity} status={status_code}",
                )
            return {
                "metered": metered_ok,
                "org_id": org_id,
                "product_code": product_code.strip(),
                "customer_identifier": customer_identifier.strip(),
                "dimension": dimension,
                "quantity": quantity,
                "metering_record_id": metering_record_id,
                "marketplace_status": status_code,
                "unprocessed_count": len(unprocessed),
            }
        except Exception as exc:
            return {
                "metered": False,
                "org_id": org_id,
                "product_code": product_code.strip(),
                "customer_identifier": customer_identifier.strip(),
                "dimension": dimension,
                "quantity": quantity,
                "reason": f"AWS Marketplace BatchMeterUsage failed ({type(exc).__name__}: {exc})",
            }


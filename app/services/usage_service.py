"""Enterprise Usage Metering & Quota Enforcement Service.

Backs real billing/usage/quota with a durable append-only ledger
(``usage_events``) instead of the previous in-memory, never-called
``PricingManager.check_and_consume_quota``.

Every billable API action appends one immutable ``UsageEvent`` row. Monthly
usage is derived by querying the ledger for the current ``YYYY-MM`` period and
is compared against the tier's ``max_monthly_api_calls`` limit from
``app.pricing.PricingManager``. Exhaustion is a hard, auditable 429.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import AuditLog, SessionLocal, UsageEvent
from app.pricing import PricingManager

logger = logging.getLogger("greencode.services.usage")


class UsageService:
    """Records metered usage events and enforces per-tier monthly quotas."""

    @staticmethod
    def _current_period() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    # ------------------------------------------------------------------
    # Metering
    # ------------------------------------------------------------------
    @classmethod
    def record_event(
        cls,
        org_id: int,
        event_type: str,
        quantity: int = 1,
        unit: str = "call",
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append one durable usage event to the billing ledger."""
        period = cls._current_period()
        db: Session = SessionLocal()
        try:
            event = UsageEvent(
                org_id=org_id,
                user_id=user_id,
                event_type=event_type,
                quantity=quantity,
                unit=unit,
                period_year_month=period,
                request_id=request_id,
            )
            db.add(event)
            db.commit()
            db.refresh(event)
            return {
                "id": event.id,
                "org_id": org_id,
                "event_type": event_type,
                "quantity": quantity,
                "unit": unit,
                "period": period,
            }
        finally:
            db.close()

    @classmethod
    def get_monthly_usage(
        cls,
        org_id: int,
        period: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """Total metered quantity for an org in a period (optionally by type)."""
        period = period or cls._current_period()
        db: Session = SessionLocal()
        try:
            q = db.query(func.coalesce(func.sum(UsageEvent.quantity), 0)).filter(
                UsageEvent.org_id == org_id,
                UsageEvent.period_year_month == period,
            )
            if event_type:
                q = q.filter(UsageEvent.event_type == event_type)
            return int(q.scalar() or 0)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Quota enforcement
    # ------------------------------------------------------------------
    @classmethod
    def check_quota(
        cls,
        org_id: int,
        tier: str,
        period: Optional[str] = None,
        event_type: str = "api_call",
    ) -> Dict[str, Any]:
        """Return the current quota status for an org without consuming."""
        period = period or cls._current_period()
        usage = cls.get_monthly_usage(org_id, period, event_type)
        limit = PricingManager.get_tier(tier).max_monthly_api_calls
        remaining = max(0, limit - usage)
        return {
            "org_id": org_id,
            "tier": tier,
            "period": period,
            "usage": usage,
            "limit": limit,
            "remaining": remaining,
            "usage_pct": round((usage / max(limit, 1)) * 100.0, 2),
            "allowed": usage < limit,
        }

    @classmethod
    def consume(
        cls,
        org_id: int,
        tier: str,
        event_type: str = "api_call",
        user_id: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Check-then-consume one billable action.

        Returns the resulting quota status. Callers must treat
        ``allowed == False`` as a hard 429 and must NOT perform the work.
        """
        status = cls.check_quota(org_id, tier, event_type=event_type)
        if not status["allowed"]:
            cls._audit_rejection(org_id, event_type, status)
            return status

        cls.record_event(
            org_id=org_id,
            event_type=event_type,
            user_id=user_id,
            request_id=request_id,
        )
        post_status = cls.check_quota(org_id, tier, event_type=event_type)
        post_status["allowed"] = True
        return post_status

    @staticmethod
    def _audit_rejection(org_id: int, event_type: str, status: Dict[str, Any]) -> None:
        db: Session = SessionLocal()
        try:
            db.add(
                AuditLog(
                    org_id=org_id,
                    action="quota:rejected",
                    resource_type="usage",
                    resource_id=event_type,
                    status="REJECTED",
                    details=(
                        f"Monthly quota exceeded for {status['tier']} tier "
                        f"({status['usage']}/{status['limit']}) on event '{event_type}'"
                    ),
                )
            )
            db.commit()
        except Exception:  # pragma: no cover - audit must never break the caller
            db.rollback()
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Usage breakdown for the customer dashboard
    # ------------------------------------------------------------------
    @classmethod
    def usage_breakdown(
        cls,
        org_id: int,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Per-event-type usage totals for the current billing period."""
        period = period or cls._current_period()
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(
                    UsageEvent.event_type,
                    func.coalesce(func.sum(UsageEvent.quantity), 0).label("total"),
                )
                .filter(
                    UsageEvent.org_id == org_id,
                    UsageEvent.period_year_month == period,
                )
                .group_by(UsageEvent.event_type)
                .all()
            )
            by_type = {row.event_type: int(row.total) for row in rows}
            return {
                "org_id": org_id,
                "period": period,
                "total_events": sum(by_type.values()),
                "by_type": by_type,
            }
        finally:
            db.close()

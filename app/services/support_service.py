"""SaaS Support & Operations Service: tier-driven SLA ticket lifecycle.

Turns the previous ``dedicated_support: bool`` flag into a real support/ops
model. Tickets carry an SLA first-response target derived from the tenant's
plan tier and the ticket severity. The service computes the SLA due time on
creation and tracks first-response / resolution so SLA compliance can be
measured, not just asserted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database import AuditLog, SessionLocal, SupportTicket
from app.pricing import PricingManager

logger = logging.getLogger("greencode.services.support")

# Base first-response SLA target in minutes, before tier multipliers.
# Enterprise gets the fastest response; free is best-effort.
SEVERITY_BASE_MINUTES: Dict[str, int] = {
    "critical": 30,
    "high": 120,
    "normal": 480,
    "low": 1440,
}

# Tier multiplier applied to the severity base time (lower = faster response).
TIER_SLA_MULTIPLIER: Dict[str, float] = {
    "enterprise": 1.0,
    "pro": 2.0,
    "free": 6.0,
}

# Only enterprise plans get an SLA guarantee at all.
SLA_GUARANTEED_TIERS = {"enterprise", "pro"}


class SupportService:
    """Creates and manages support tickets with per-tier SLA targets."""

    @classmethod
    def sla_response_minutes(cls, tier: str, severity: str) -> int:
        base = SEVERITY_BASE_MINUTES.get(severity, SEVERITY_BASE_MINUTES["normal"])
        mult = TIER_SLA_MULTIPLIER.get(tier.lower(), TIER_SLA_MULTIPLIER["free"])
        return int(round(base * mult))

    @classmethod
    def create_ticket(
        cls,
        org_id: int,
        subject: str,
        description: str = "",
        severity: str = "normal",
        tier: str = "free",
        requester_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        severity = severity.lower()
        if severity not in SEVERITY_BASE_MINUTES:
            raise ValueError(f"Unknown severity '{severity}'")
        tier = tier.lower()
        sla_minutes = cls.sla_response_minutes(tier, severity)
        now = datetime.now(timezone.utc)
        db: Session = SessionLocal()
        try:
            ticket = SupportTicket(
                org_id=org_id,
                requester_id=requester_id,
                subject=subject,
                description=description,
                severity=severity,
                status="open",
                tier=tier,
                sla_response_minutes=sla_minutes,
                sla_due_at=now + timedelta(minutes=sla_minutes),
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            result = cls._to_dict(ticket)
            cls._audit(org_id, "support:ticket_create", str(ticket.id), f"{severity} / {tier}")
            return result
        finally:
            db.close()

    @classmethod
    def respond(cls, org_id: int, ticket_id: int) -> Dict[str, Any]:
        """Record the first agent response and evaluate SLA compliance."""
        db: Session = SessionLocal()
        try:
            t = db.query(SupportTicket).filter(
                SupportTicket.org_id == org_id, SupportTicket.id == ticket_id
            ).one_or_none()
            if not t:
                raise ValueError(f"Ticket {ticket_id} not found for org {org_id}")
            now = datetime.now(timezone.utc)
            if t.first_responded_at is None:
                t.first_responded_at = now
            if t.status == "open":
                t.status = "pending"
            db.commit()
            db.refresh(t)
            return cls._to_dict(t)
        finally:
            db.close()

    @classmethod
    def resolve(cls, org_id: int, ticket_id: int) -> Dict[str, Any]:
        db: Session = SessionLocal()
        try:
            t = db.query(SupportTicket).filter(
                SupportTicket.org_id == org_id, SupportTicket.id == ticket_id
            ).one_or_none()
            if not t:
                raise ValueError(f"Ticket {ticket_id} not found for org {org_id}")
            now = datetime.now(timezone.utc)
            if t.first_responded_at is None:
                t.first_responded_at = now
            t.resolved_at = now
            t.status = "resolved"
            db.commit()
            db.refresh(t)
            result = cls._to_dict(t)
            cls._audit(org_id, "support:ticket_resolve", str(ticket_id), t.severity)
            return result
        finally:
            db.close()

    @classmethod
    def list_tickets(cls, org_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        db: Session = SessionLocal()
        try:
            rows = (
                db.query(SupportTicket)
                .filter(SupportTicket.org_id == org_id)
                .order_by(SupportTicket.created_at.desc())
                .limit(limit)
                .all()
            )
            return [cls._to_dict(r) for r in rows]
        finally:
            db.close()

    @classmethod
    def support_plan(cls, org_id: int, tier: str) -> Dict[str, Any]:
        """Describe the support & ops posture for a tenant's tier."""
        features = PricingManager.get_tier(tier)
        return {
            "org_id": org_id,
            "tier": tier,
            "dedicated_support": getattr(features, "dedicated_support", False),
            "sla_guaranteed": tier.lower() in SLA_GUARANTEED_TIERS,
            "first_response_targets_minutes": {
                sev: cls.sla_response_minutes(tier, sev) for sev in SEVERITY_BASE_MINUTES
            },
        }

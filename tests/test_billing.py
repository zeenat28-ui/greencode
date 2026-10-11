"""Enterprise Billing & Quota Test Suite.

Validates the durable usage-metering / quota-enforcement service and the
billing router endpoints (subscription lifecycle, invoice generation, pay,
usage snapshot). Covers service-level behaviour plus the HTTP surface with
auth and tenant-isolation checks.
"""

import pytest
from fastapi.testclient import TestClient

from app.database import init_db, SessionLocal
from app.main import app
from app.auth.jwt import create_tokens
from app.auth.roles import Role, Permission
from app.services.billing_service import BillingService

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    init_db(use_alembic=False)


def _admin_headers(role=Role.SUPERADMIN, org_id=1):
    tokens = create_tokens(user_id=1, org_id=org_id, role=role)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _guest_headers():
    return {"Authorization": "Bearer invalid-token"}


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------
def test_create_and_read_subscription():
    sub = BillingService.create_subscription(org_id=1, tier="pro", seats=3)
    assert sub["tier"] == "pro"
    assert sub["seats"] == 3
    assert sub["status"] == "active"

    read = BillingService.get_subscription(org_id=1)
    assert read is not None
    assert read["tier"] == "pro"
    assert read["seats"] == 3


def test_ensure_subscription_creates_free_when_absent():
    BillingService.create_subscription(org_id=2, tier="pro")
    free = BillingService.ensure_subscription(org_id=3, tier="free")
    assert free["tier"] == "free"
    assert BillingService.get_subscription(org_id=3)["tier"] == "free"


def test_change_tier_and_set_seats():
    BillingService.create_subscription(org_id=4, tier="pro", seats=2)
    changed = BillingService.change_tier(org_id=4, new_tier="enterprise", seats=5)
    assert changed["tier"] == "enterprise"
    assert changed["seats"] == 5

    set_seats = BillingService.set_seats(org_id=4, seats=10)
    assert set_seats["seats"] == 10


def test_generate_and_retrieve_invoice():
    BillingService.create_subscription(org_id=5, tier="pro", seats=2)
    inv = BillingService.generate_invoice(org_id=5, period="2026-10")
    assert inv["invoice_number"].startswith("GC-202610-0001")
    assert inv["period"] == "2026-10"
    assert inv["status"] == "open"

    fetched = BillingService.get_invoice(org_id=5, invoice_number=inv["invoice_number"])
    assert fetched is not None
    assert fetched["total_amount_usd"] >= 0

    paid = BillingService.mark_invoice_paid(org_id=5, invoice_number=inv["invoice_number"])
    assert paid["status"] == "paid"


def test_list_invoices_returns_ordered_history():
    BillingService.create_subscription(org_id=6, tier="free")
    a = BillingService.generate_invoice(org_id=6, period="2026-09")
    b = BillingService.generate_invoice(org_id=6, period="2026-10")
    Invoices = BillingService.list_invoices(org_id=6, limit=10)
    assert [inv["invoice_number"] for inv in Invoices] == [
        b["invoice_number"],
        a["invoice_number"],
    ]


def test_usage_snapshot_and_quota():
    BillingService.create_subscription(org_id=7, tier="free")
    snapshot = BillingService.usage_snapshot(org_id=7)
    assert snapshot["subscription"]["tier"] == "free"
    assert snapshot["quota"]["tier"] == "free"
    assert "breakdown" in snapshot


def test_consume_quota_enforces_limit():
    BillingService.create_subscription(org_id=8, tier="free")
    for _ in range(100):
        status = BillingService.consume(org_id=8, tier="free", event_type="api_call")
        assert status["allowed"] is True
    exhausted = BillingService.consume(org_id=8, tier="free", event_type="api_call")
    assert exhausted["allowed"] is False
    assert exhausted["usage"] == 100
    assert exhausted["limit"] == 100
# ---------------------------------------------------------------------------
# Router-level tests
# ---------------------------------------------------------------------------
def test_subscription_create_endpoint():
    headers = _admin_headers()
    res = client.post(
        "/api/billing/subscription",
        json={"org_id": 10, "tier": "pro", "seats": 2, "status": "active"},
        headers=headers,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["tier"] == "pro"
    assert body["seats"] == 2


def test_tenant_isolation_on_billing_write():
    res = client.post(
        "/api/billing/subscription",
        json={"org_id": 20, "tier": "pro"},
        headers=_admin_headers(org_id=1),
    )
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


def test_anonymous_billing_write_is_denied():
    res = client.post("/api/billing/subscription", json={"org_id": 1, "tier": "pro"})
    assert res.status_code == 401


def test_invoice_generation_endpoint():
    headers = _admin_headers()
    res = client.post(
        "/api/billing/invoice",
        json={"org_id": 11, "period": "2026-10"},
        headers=headers,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["invoice_number"].startswith("GC-202610-0001")


def test_pay_invoice_endpoint():
    headers = _admin_headers()
    invoice = BillingService.generate_invoice(org_id=12, period="2026-10")
    res = client.post(
        f"/api/billing/invoice/{invoice['invoice_number']}/pay",
        params={"org_id": 12},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "paid"


def test_cross_tenant_billing_read_is_denied():
    res = client.get(
        "/api/billing/usage",
        params={"org_id": 99},
        headers=_admin_headers(org_id=1),
    )
    assert res.status_code == 403
    assert "Tenant isolation violation" in res.json()["detail"]


def test_guest_billing_read_is_denied():
    res = client.get("/api/billing/invoices", params={"org_id": 1})
    assert res.status_code == 401

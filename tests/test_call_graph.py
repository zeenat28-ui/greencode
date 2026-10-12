"""Tests for Cross-File Inter-Procedural Call Graph Analyzer (app/call_graph.py)."""

from fastapi.testclient import TestClient

from app.call_graph import audit_cross_file_loops
from app.main import app
from app.sdk import GreenCodeSDK


def test_transitive_three_file_call_graph_detection():
    files = {
        "db_layer.py": (
            "def run_sql_query(session, order_id):\n"
            "    return session.execute('SELECT * FROM invoices WHERE id = :id', {'id': order_id})\n"
        ),
        "billing_service.py": (
            "from db_layer import run_sql_query\n\n"
            "def load_order_invoice(session, order_id):\n"
            "    return run_sql_query(session, order_id)\n"
        ),
        "orders_controller.py": (
            "from billing_service import load_order_invoice\n\n"
            "def process_batch(session, order_ids):\n"
            "    results = []\n"
            "    for oid in order_ids:\n"
            "        results.append(load_order_invoice(session, oid))\n"
            "    return results\n"
        ),
    }

    report = audit_cross_file_loops(files)
    assert report["files_scanned"] == 3
    assert report["symbols_indexed"] >= 3
    assert report["total_violations"] == 1
    assert report["green_score"] < 100.0

    violation = report["violations"][0]
    assert violation["file_path"] == "orders_controller.py"
    assert violation["violation_type"] == "CROSS_FILE_DB_IN_LOOP"
    assert "billing_service.py:load_order_invoice" in violation["call_chain"]
    assert "db_layer.py:run_sql_query" in violation["call_chain"]


def test_call_graph_http_endpoint_and_sdk():
    files = {
        "net_client.py": (
            "import requests\n\n"
            "def fetch_remote_price(sku):\n"
            "    return requests.get(f'https://pricing.internal/{sku}')\n"
        ),
        "checkout.py": (
            "from net_client import fetch_remote_price\n\n"
            "def total_cart(skus):\n"
            "    for sku in skus:\n"
            "        fetch_remote_price(sku)\n"
        ),
    }

    sdk = GreenCodeSDK()
    sdk_res = sdk.audit_call_graph(files)
    assert sdk_res["total_violations"] == 1
    assert sdk_res["violations"][0]["violation_type"] == "CROSS_FILE_NETWORK_IN_LOOP"

    client = TestClient(app)
    resp = client.post("/api/audit/call-graph", json={"files": files})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_violations"] == 1
    assert body["violations"][0]["callee_file"] == "net_client.py"


"""Prove the slim container exposes the real MCP tools (not just discovery docs).

Does a Streamable-HTTP initialize handshake, then lists tools. Confirms the
audit engine imported cleanly inside the image (tree-sitter grammars loaded),
which is the thing most likely to break in a slim build.
"""
import json
import sys
import urllib.request

import requests


def main(base, token="test-token-123"):
    s = requests.Session()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    init = {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "deploy-smoke", "version": "1.0"},
        },
    }
    r = s.post(f"{base}/mcp", headers=headers, json=init, timeout=30)
    print("initialize status:", r.status_code)
    sid = r.headers.get("Mcp-Session-Id")
    print("session id:", bool(sid))
    if sid:
        headers["Mcp-Session-Id"] = sid
    # client initialized notification
    s.post(f"{base}/mcp", headers=headers, json={
        "jsonrpc": "2.0", "method": "notifications/initialized"}, timeout=30)
    r2 = s.post(f"{base}/mcp", headers=headers, json={
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, timeout=30)
    print("tools/list status:", r2.status_code)
    try:
        # Streamable HTTP may answer as SSE ("event: message\ndata: {...}")
        # or as plain JSON depending on transport negotiation. Handle both.
        text = r2.text
        payload = None
        if text.lstrip().startswith("{"):
            payload = r2.json()
        else:
            for line in text.splitlines():
                if line.startswith("data:"):
                    payload = json.loads(line[5:].strip())
                    break
        tools = payload.get("result", {}).get("tools", [])
        print(f"TOOL COUNT: {len(tools)}")
        print("TOOLS:", ", ".join(sorted(t["name"] for t in tools)))
        ok = len(tools) > 0
    except Exception as e:
        print("parse error:", e, r2.text[:300])
        ok = False
    print("-" * 40)
    print("ENGINE OK" if ok else "ENGINE FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8137"
    main(base)

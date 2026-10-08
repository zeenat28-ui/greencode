"""Alexa+ compliance live check: boot the real server over a socket and prove
the exact checklist items the Alexa+ MCP quickstart requires.

Checks, in order:
  1-3  Protected Resource Metadata (RFC 9728) at the well-known URI, at the
       resource-specific path, describing the resource as https:// behind a
       forwarded proto (i.e. behind cloudflared).
  4    Authorization server metadata (RFC 8414) including PKCE S256.
  5-6  401 Unauthorized WITHOUT a WWW-Authenticate header for unauthenticated
       GET and POST to /mcp.
  7    401 for a wrong bearer token.
  8    Full MCP initialize handshake WITH the token (protocol >= 2025-11-25).
  9    tools/list through the authenticated session.
 10    Warm round-trip latency of every decision-making tool, each measured
       twice: a cold call (network allowed) and a warm call that must land
       under the official 500 ms budget.
"""
import argparse
import asyncio
import json
import os
import socket
import threading
import time

import httpx
import uvicorn

from app.mcp_server import create_app
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

PORT = 8792
LOCAL_BASE = f"http://127.0.0.1:{PORT}"
TOKEN = "greencode-alexa-live-token"
BUDGET_MS = 500

SNIPPET = (
    "def process(rows):\n"
    "    total = 0\n"
    "    log = \"\"\n"
    "    for a in rows:\n"
    "        for b in rows:\n"
    "            total += a * b\n"
    "            log = log + str(a) + str(b)\n"
    "    return total, log\n"
)


def wait_for_port(port, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


def check_discovery(failures, base, remote=False):
    print("-" * 62)
    print("Discovery documents (RFC 9728 / RFC 8414)")
    with httpx.Client(base_url=base, timeout=20) as client:
        prm = client.get("/.well-known/oauth-protected-resource")
        if prm.status_code != 200 or not prm.json().get("resource", "").endswith("/mcp"):
            failures.append(f"PRM well-known document broken: {prm.status_code} {prm.text[:120]}")
        else:
            print(f"1  PRM well-known      : OK  resource={prm.json()['resource']}")

        prm2 = client.get("/.well-known/oauth-protected-resource/mcp")
        if prm2.status_code != 200:
            failures.append(f"PRM resource-specific path broken: {prm2.status_code}")
        else:
            print("2  PRM /mcp path       : OK")

        if remote:
            # Through the tunnel cloudflared sets the public Host and terminates
            # TLS: the document must advertise its public https:// identity.
            resource = prm.json().get("resource", "")
            if not (resource.startswith("https://") and resource.endswith("/mcp")):
                failures.append(f"PRM through tunnel does not report https:// {resource}")
            else:
                print(f"3  PRM behind tunnel    : OK  reports {resource}")
        else:
            # Behave like a tunnel: TLS terminated in front, loopback behind it.
            fwd = client.get(
                "/.well-known/oauth-protected-resource",
                headers={"X-Forwarded-Proto": "https", "Host": "mcp.example.com"},
            )
            if fwd.json().get("resource") != "https://mcp.example.com/mcp":
                failures.append(f"PRM ignores forwarded proto: {fwd.json()}")
            else:
                print("3  PRM behind tunnel    : OK  reports https:// URL")

        asmd = client.get("/.well-known/oauth-authorization-server")
        methods = asmd.json().get("code_challenge_methods_supported", []) if asmd.status_code == 200 else []
        if asmd.status_code != 200 or "S256" not in methods:
            failures.append(f"AS metadata missing or no S256: {asmd.status_code} {methods}")
        else:
            print(f"4  AS metadata + S256   : OK  methods={methods}")


def check_401(failures, base):
    print("-" * 62)
    print("401 checklist (no WWW-Authenticate header)")
    body = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    accept = {"Accept": "application/json, text/event-stream"}
    with httpx.Client(base_url=base, timeout=20) as client:
        get = client.get("/mcp", headers=accept)
        hdrs = {k.lower() for k in get.headers}
        if get.status_code != 401 or "www-authenticate" in hdrs:
            failures.append(f"unauthenticated GET must be 401 without WWW-Authenticate, got {get.status_code} {sorted(hdrs)}")
        else:
            print("5  GET no token        : 401, no WWW-Authenticate")

        post = client.post("/mcp", json=body, headers=accept)
        hdrs = {k.lower() for k in post.headers}
        if post.status_code != 401 or "www-authenticate" in hdrs:
            failures.append(f"unauthenticated POST must be 401 without WWW-Authenticate, got {post.status_code}")
        else:
            print("6  POST no token       : 401, no WWW-Authenticate")

        wrong = client.post("/mcp", json=body, headers={**accept, "Authorization": "Bearer nope"})
        if wrong.status_code != 401:
            failures.append(f"wrong token must be 401, got {wrong.status_code}")
        else:
            print("7  Wrong token         : 401")


async def run_session_checks(failures, mcp_url, token):
    print("-" * 62)
    print("Authenticated MCP session + latency budget (<500 ms warm)")
    import httpx2

    # This MCP SDK version threads auth through an httpx2 client rather than
    # a headers= argument; default headers ride on every request it makes.
    authed_http = httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}, timeout=30
    )
    try:
        async with streamable_http_client(mcp_url, http_client=authed_http) as streams:
            read, write = streams[0], streams[1]
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                print(f"8  initialize          : OK  protocol={init.protocol_version} "
                      f"server={init.server_info.name}")
                if init.protocol_version < "2025-11-25":
                    failures.append(f"protocol {init.protocol_version} below hackathon minimum")

                tools = await session.list_tools()
                print(f"9  tools/list          : OK  {len(tools.tools)} tools")

                async def timed_call(name, args):
                    start = time.perf_counter()
                    res = await session.call_tool(name, args)
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    payload = json.loads(res.content[0].text)
                    return elapsed_ms, payload

                calls = [
                    ("audit_code", {"source_code": SNIPPET}),
                    ("measure_energy", {}),
                    ("get_grid_intensity", {"zone": "US-CAL-CISO"}),
                    ("calculate_sci", {"energy_joules": 1500.0,
                                       "duration_seconds": 30.0,
                                       "functional_unit": 10000.0}),
                    ("compare_regions", {"zones": ["IE", "US-VA", "FR"]}),
                    ("audit_and_score", {"source_code": SNIPPET}),
                ]

                print("-" * 62)
                print(f"{'tool':<20} {'cold ms':>9} {'warm ms':>9}  verdict")
                for name, args in calls:
                    cold_ms, cold_payload = await timed_call(name, args)
                    warm_ms, warm_payload = await timed_call(name, args)
                    ok = cold_payload.get("status") == "ok" and warm_payload.get("status") == "ok"
                    verdict = "ok" if ok else f"status={warm_payload.get('status')}"
                    if not ok:
                        failures.append(f"{name} returned status={warm_payload.get('status')}")
                    if warm_ms >= BUDGET_MS:
                        failures.append(
                            f"{name} warm round trip {warm_ms:.0f} ms >= {BUDGET_MS} ms budget"
                        )
                        verdict = f"OVER BUDGET ({warm_ms:.0f} ms)"
                    else:
                        verdict = f"{verdict}, warm within budget"
                    print(f"{name:<20} {cold_ms:>9.0f} {warm_ms:>9.0f}  {verdict}")
    finally:
        await authed_http.aclose()

    return failures


def parse_args():
    ap = argparse.ArgumentParser(
        description="Alexa+ MCP compliance live check. Boots a local server by "
        "default; pass --url to check an already-running deployment "
        "(e.g. the https://*.trycloudflare.com tunnel)."
    )
    ap.add_argument(
        "--url",
        default=None,
        help="Base URL of a running server, e.g. https://abc-xyz.trycloudflare.com",
    )
    ap.add_argument(
        "--token",
        default=None,
        help="Bearer token the server enforces (default: GREENCODE_MCP_TOKEN env "
        f"or the built-in local token {TOKEN!r})",
    )
    return ap.parse_args()


def main():
    args = parse_args()
    token = args.token or os.environ.get("GREENCODE_MCP_TOKEN") or TOKEN

    server = None
    thread = None
    if args.url:
        base = args.url.rstrip("/")
    else:
        # The token must be in the environment before create_app() reads it.
        os.environ["GREENCODE_MCP_TOKEN"] = token
        config = uvicorn.Config(create_app(), host="127.0.0.1", port=PORT,
                                log_level="error")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        if not wait_for_port(PORT):
            print("FAIL: server did not start")
            return 1
        base = LOCAL_BASE

    print("=" * 62)
    print(f"Alexa+ MCP compliance live check  ({base})")
    print("=" * 62)
    failures = []
    check_discovery(failures, base, remote=bool(args.url))
    check_401(failures, base)
    asyncio.run(run_session_checks(failures, f"{base}/mcp", token))

    if server is not None:
        server.should_exit = True
        thread.join(timeout=10)

    print("=" * 62)
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("ALL ALEXA+ COMPLIANCE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""End-to-end MCP test: boot the server over Streamable HTTP and call it as a
real MCP client would - the same path an Alexa+ agent takes.
"""
import asyncio
import json
import os
import socket
import threading
import time

import uvicorn

from app.mcp_server import create_app
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

PORT = 8791
URL = f"http://127.0.0.1:{PORT}/mcp"

# The app's import chain loads .env, so a GREENCODE_MCP_TOKEN there turns the
# 401 checklist on for this in-process server too. Send it like a real Alexa+
# agent would; with no token set the server runs open and no client is passed.
_TOKEN = os.environ.get("GREENCODE_MCP_TOKEN", "").strip()


def _authed_http():
    if not _TOKEN:
        return None
    import httpx2
    return httpx2.AsyncClient(headers={"Authorization": f"Bearer {_TOKEN}"}, timeout=30)

HEAVY = """
def process(rows):
    total = 0
    log = ""
    for a in rows:
        for b in rows:
            for c in rows:
                total += a * b * c
                log = log + f"{a}{b}{c}\\n"
    return total, log
"""


def wait_for_port(port, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False
async def run_checks():
    failures = []

    async with streamable_http_client(URL, http_client=_authed_http()) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"1 initialize        : OK  server={init.server_info.name} "
                  f"v{init.server_info.version} protocol={init.protocol_version}")
            assert init.protocol_version >= "2025-11-25", init.protocol_version

            tools = await session.list_tools()
            print(f"2 tools/list        : OK  {len(tools.tools)} tools advertised")

            health = await session.read_resource("greencode://health")
            payload = json.loads(health.contents[0].text)
            print(f"3 resource health   : OK  protocol={payload['mcp_protocol_version']} "
                  f"energy={payload['energy_backend']['best_available']}")

            std = await session.read_resource("greencode://standards/gsf-sci")
            print(f"4 resource sci spec : OK  {json.loads(std.contents[0].text)['formula']}")

            res = await session.call_tool("audit_code", {"source_code": HEAVY})
            payload = json.loads(res.content[0].text)
            data = payload["data"]
            print(f"5 audit_code        : score={data['green_score']} grade={data['grade']} "
                  f"violations={data['violation_count']}")
            if data["violation_count"] == 0:
                failures.append("audit_code found no violations in a triple-nested loop")

            res = await session.call_tool("audit_and_score", {"source_code": HEAVY})
            payload = json.loads(res.content[0].text)
            data = payload["data"]
            print(f"6 audit_and_score   : grade={data['grade']} "
                  f"plan={len(data['remediation_plan'])} steps "
                  f"sci={'yes' if data['sci'] else 'no'}")
            if not data["remediation_plan"]:
                failures.append("audit_and_score produced an empty remediation plan")
            if payload["warnings"]:
                print(f"   provenance warning: {payload['warnings'][0][:68]}...")

            res = await session.call_tool("measure_energy", {})
            data = json.loads(res.content[0].text)["data"]
            print(f"7 measure_energy    : {data['energy_joules']:.2f} J via "
                  f"{data['measurement_method']} (hardware={data['measurement_is_hardware']})")

            res = await session.call_tool("calculate_sci", {
                "energy_joules": 1500.0,
                "duration_seconds": 30.0,
                "functional_unit": 10000.0,
            })
            payload = json.loads(res.content[0].text)
            if payload["status"] == "ok":
                sci_d = payload["data"]["sci"]
                print(f"8 calculate_sci     : SCI="
                      f"{sci_d['sci_gco2_per_functional_unit']:.3e} gCO2e/unit")
            else:
                print(f"8 calculate_sci     : DEGRADED "
                      f"({payload['data'].get('reason', '')[:56]})")

            res = await session.call_tool("compare_regions",
                                          {"zones": ["IE", "US-VA", "FR"]})
            payload = json.loads(res.content[0].text)
            clean = payload["data"].get("cleanest")
            if clean:
                print(f"9 compare_regions   : cleanest={clean['zone']} "
                      f"({clean['carbon_intensity']} gCO2e/kWh)")
            else:
                print("9 compare_regions   : DEGRADED (no live intensity)")

            res = await session.call_tool("audit_code", {"source_code": ""})
            payload = json.loads(res.content[0].text)
            print(f"10 empty input      : status={payload['status']} (graceful)")
            if payload["status"] != "error":
                failures.append("empty source did not return status=error")

            res = await session.call_tool("compare_regions", {"zones": ["IE"]})
            if json.loads(res.content[0].text)["status"] != "error":
                failures.append("single-zone compare did not return status=error")
            print("11 validation       : bad input rejected")

    return failures
def main():
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=PORT,
                            log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not wait_for_port(PORT):
        print("FAIL: server did not start")
        return 1

    print("=" * 62)
    print("Live MCP session over Streamable HTTP")
    print("=" * 62)
    failures = asyncio.run(run_checks())
    server.should_exit = True
    thread.join(timeout=10)

    print("=" * 62)
    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("ALL LIVE MCP CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


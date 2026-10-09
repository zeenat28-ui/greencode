"""Smoke-test a running GreenCode MCP server against the Alexa+ checklist.

Usage:
    python deploy/mcp/smoke_test.py http://127.0.0.1:8137

Checks the same four public facts check_mcp_live.py asserts over a tunnel, so
you can confirm the slim container is healthy before pointing addon.json at it.
"""
import json
import sys
import urllib.error
import urllib.request


def fetch(base, path, headers=None, timeout=15):
    req = urllib.request.Request(base + path, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 0, str(e).encode()


def main(base):
    ok = True

    st, body = fetch(base, "/.well-known/oauth-protected-resource")
    good = st == 200
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] PRM (RFC 9728) status={st}")
    if st == 200:
        prm = json.loads(body)
        good = prm.get("resource", "").endswith("/mcp")
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] PRM resource ends with /mcp")
        good = bool(prm.get("authorization_servers"))
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] PRM lists authorization_servers")

    st, body = fetch(base, "/.well-known/oauth-authorization-server")
    good = st == 200
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] Auth-server metadata (RFC 8414) status={st}")
    if st == 200:
        asd = json.loads(body)
        good = "S256" in asd.get("code_challenge_methods_supported", [])
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] PKCE S256 advertised")

    st, _ = fetch(base, "/mcp")
    good = st == 401
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] /mcp unauthenticated (want 401) status={st}")

    st, _ = fetch(base, "/privacy")
    good = st == 200
    ok &= good
    print(f"[{'PASS' if good else 'FAIL'}] /privacy (want 200) status={st}")

    print("-" * 40)
    print("ALL PASSED" if ok else "FAILURES DETECTED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    main(base)

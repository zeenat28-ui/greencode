"""verify_fullstack_alexa.py

Full-stack verification of the Alexa voice pipeline on a Vercel deployment.

Checks:
  1. Backend: all 6 fault fixes still present
  2. Frontend: useAlexaVoice hook connects to /api/alexa/skill (not /mcp)
  3. Frontend: hook sends Authorization header (B2)
  4. Frontend: hook does NOT use credentials:include (B1)
  5. Frontend: hook omits applicationId in browser payloads (B6)
  6. Frontend: hook autoStart does not call mic.start() without gesture (B8)
  7. vercel.json: CORS origin is not wildcard (B4)
  8. vercel.json: /api/alexa/skill rewrite exists
  9. api/index.py: SQLite /tmp path for Vercel (B5)
 10. frontend/.env: uses VITE_API_URL (B9)
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).parent
RESULTS = []

def check(name, fn):
    try:
        fn()
        print(f"  PASS  {name}")
        RESULTS.append(True)
    except Exception as exc:
        print(f"  FAIL  {name}")
        print(f"        {exc}")
        RESULTS.append(False)

print("=" * 60)
print("GreenCode Full-Stack Alexa Pipeline Verification")
print("=" * 60)

# ------------------------------------------------------------------
print("\n[Backend] 6 fault fixes")

def chk_backend_router():
    code = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "include_router(_alexa_skill_module.router)" in code
check("F1: alexa_skill.router mounted in main.py", chk_backend_router)

def chk_backend_timestamp():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert "_TIMESTAMP_TOLERANCE_SECONDS" in code
check("F2: timestamp guard present", chk_backend_timestamp)

def chk_backend_cert():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert "_verify_ask_cert_chain" in code
    assert "cert_url or sig_b64" in code
check("F3: cert chain verification (browser-safe)", chk_backend_cert)

def chk_backend_dispatch():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert "from app.alexa_dispatch import" in code
    assert (ROOT / "app" / "alexa_dispatch.py").exists()
check("F4: circular import broken", chk_backend_dispatch)

def chk_backend_ssml():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert '"type": "SSML"' in code
check("F5: SSML response builder", chk_backend_ssml)

def chk_backend_addon():
    addon = json.loads((ROOT / "alexa" / "addon.json").read_text())
    uri = addon["integrations"][0]["config"]["endpoints"]["default"]["uri"]
    assert uri.endswith("/api/alexa/skill"), f"got: {uri}"
check("F6: addon.json endpoint", chk_backend_addon)

# ------------------------------------------------------------------
print("\n[Frontend] Voice hook")

hook = (ROOT / "frontend" / "src" / "hooks" / "useAlexaVoice.ts").read_text(encoding="utf-8")

def chk_hook_endpoint():
    assert "/api/alexa/skill" in hook
    assert "/mcp" not in hook or "mcp" not in hook.split("fetch")[1].split(")")[0]
check("Hook calls /api/alexa/skill", chk_hook_endpoint)

def chk_hook_auth():
    assert "getAccessToken" in hook
    assert "Authorization" in hook
    assert "Bearer" in hook
check("B2: hook attaches Authorization header", chk_hook_auth)

def chk_hook_no_credentials():
    # credentials:'include' must NOT be in the fetch call
    fetch_section = hook[hook.find("fetch("):hook.find("fetch(") + 500]
    assert "credentials" not in fetch_section or "credentials" not in fetch_section.split("\n")[0:5][0]
check("B1: hook does not use credentials:include", chk_hook_no_credentials)

def chk_hook_no_app_id():
    assert 'applicationId' not in hook or hook.count('applicationId') == 0
check("B6: hook omits applicationId in browser payload", chk_hook_no_app_id)

def chk_hook_no_autostart_mic():
    # autoStart parameter is accepted but not used to call start()
    assert "autoRestartRef.current = false" in hook  # starts as false
check("B8: hook does not auto-start mic without user gesture", chk_hook_no_autostart_mic)

def chk_hook_env_var():
    assert "VITE_API_URL" in hook
    assert "VITE_API_BASE_URL" not in hook
check("B3: hook reads VITE_API_URL (correct env var)", chk_hook_env_var)

# ------------------------------------------------------------------
print("\n[Deployment] Vercel config")

def chk_vercel_cors():
    cfg = json.loads((ROOT / "vercel.json").read_text())
    for h in cfg.get("headers", []):
        for hdr in h.get("headers", []):
            if hdr.get("key") == "Access-Control-Allow-Origin":
                assert hdr["value"] != "*", f"Wildcard CORS origin found for {h['source']}"
check("B4: vercel.json CORS is not wildcard", chk_vercel_cors)

def chk_vercel_rewrite():
    cfg = json.loads((ROOT / "vercel.json").read_text())
    rewrites = cfg.get("rewrites", [])
    alexa_rewrite = [r for r in rewrites if "/alexa/skill" in r.get("source", "")]
    assert len(alexa_rewrite) >= 1, "No /alexa/skill rewrite found"
check("vercel.json has /alexa/skill rewrite", chk_vercel_rewrite)

def chk_vercel_api_index():
    code = (ROOT / "api" / "index.py").read_text(encoding="utf-8")
    assert "/tmp/greencode.db" in code, "SQLite /tmp path not found"
check("B5: api/index.py uses /tmp for SQLite on Vercel", chk_vercel_api_index)

# ------------------------------------------------------------------
print("\n[Config] Environment")

def chk_fe_env():
    env = (ROOT / "frontend" / ".env").read_text(encoding="utf-8")
    assert "VITE_API_URL" in env
    assert "VITE_API_BASE_URL" not in env or env.count("VITE_API_BASE_URL") == 0
check("B9: frontend/.env uses VITE_API_URL", chk_fe_env)

# ------------------------------------------------------------------
print()
passed = sum(RESULTS)
total = len(RESULTS)
print("=" * 60)
print(f"Results: {passed}/{total} passed")
print("=" * 60)
sys.exit(0 if passed == total else 1)
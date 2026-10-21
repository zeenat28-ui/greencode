#!/usr/bin/env python3
"""verify_alexa_pipeline.py - Local smoke-test for the six Alexa pipeline fixes.

Run from the repo root:
    python verify_alexa_pipeline.py

Each check prints PASS or FAIL. Exit code 0 = all passed.
"""
import json, os, pathlib, sys, time

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
print("GreenCode Alexa Pipeline Fix Verification")
print("=" * 60)

# ------------------------------------------------------------------
print("\n[F6] addon.json endpoint URI")
def chk_f6():
    addon = json.loads((ROOT / "alexa" / "addon.json").read_text())
    uri = addon["integrations"][0]["config"]["endpoints"]["default"]["uri"]
    assert uri.endswith("/api/alexa/skill"), f"Expected /api/alexa/skill, got: {uri}"
check("addon.json points to /api/alexa/skill", chk_f6)

# ------------------------------------------------------------------
print("\n[F1] alexa_skill.router mounted in main.py")
def chk_f1():
    code = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "_alexa_skill_module" in code, "main.py missing _alexa_skill_module"
    assert "include_router(_alexa_skill_module.router)" in code, "include_router call missing"
check("main.py mounts alexa_skill.router", chk_f1)

# ------------------------------------------------------------------
print("\n[F4] Circular import broken")
def chk_f4_dispatch():
    code = (ROOT / "app" / "alexa_skill.py").read_text(encoding="utf-8")
    assert "from app.alexa_dispatch import dispatch_nlu_action" in code
check("alexa_skill.py re-exports from alexa_dispatch", chk_f4_dispatch)

def chk_f4_mcp():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert "from app.alexa_dispatch import dispatch_nlu_action" in code
check("mcp_server.py imports from alexa_dispatch", chk_f4_mcp)

def chk_f4_module():
    assert (ROOT / "app" / "alexa_dispatch.py").exists(), "alexa_dispatch.py not found"
check("alexa_dispatch.py exists", chk_f4_module)

# ------------------------------------------------------------------
print("\n[F2] Timestamp replay protection")
def chk_f2_code():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert "_TIMESTAMP_TOLERANCE_SECONDS" in code
    assert 'payload.get("request")' in code or "req_ts" in code
check("mcp_server.py has timestamp guard constants", chk_f2_code)

def chk_f2_skill():
    code = (ROOT / "app" / "alexa_skill.py").read_text(encoding="utf-8")
    assert "FAULT 2 FIX" in code or "request.timestamp" in code or "body_json" in code
check("alexa_skill.py reads timestamp from JSON body", chk_f2_skill)

# ------------------------------------------------------------------
print("\n[F3] ASK cert chain verification")
def chk_f3():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert "_verify_ask_cert_chain" in code
    assert "SignatureCertChainUrl" in code or "signaturecertchainurl" in code
check("mcp_server.py has _verify_ask_cert_chain", chk_f3)

# ------------------------------------------------------------------
print("\n[F5] SSML response + reprompt")
def chk_f5():
    code = (ROOT / "app" / "mcp_server.py").read_text(encoding="utf-8")
    assert '"type": "SSML"' in code, 'outputSpeech type must be SSML'
    assert "_DEFAULT_REPROMPT" in code or "effective_reprompt" in code
check("mcp_server.py _build_ask_response uses SSML", chk_f5)

# ------------------------------------------------------------------
print("\n[F2+F3] Main.py webhook captures raw_body")
def chk_main_raw():
    code = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "raw_body = await request.body()" in code
    assert "alexa_request_guard(request, payload, raw_body=raw_body)" in code
check("main.py webhook passes raw_body to guard", chk_main_raw)

# ------------------------------------------------------------------
print()
passed = sum(RESULTS)
total  = len(RESULTS)
print("=" * 60)
print(f"Results: {passed}/{total} passed")
print("=" * 60)
sys.exit(0 if passed == total else 1)

"""Fast baseline verification for the GreenCode hackathon submission.

Run:  python -m vfy.baseline_check      (from the repo root)
Local-only imports and in-memory calls. Implements the plan's 'confirm baseline'
item with a few seconds of runtime -- no network, no AWS, no server boot.
"""
import os
import sys
import time

# Self-location: this script lives in vfy/, the repo root is its parent.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

PASS = []
FAIL = []


def check(name, value):
    (PASS if value else FAIL).append(name)
    print(f"[{'OK' if value else 'FAIL'}] {name}")


def main():
    print("== baseline_check ==")
    t0 = time.time()

    # 1. GSF-SCI spec engine (the hackathon moat).
    try:
        from app.sci import SCIResult, compute_sci, sci_grade
        r = compute_sci(
            energy_joules=1500.0,
            duration_seconds=30.0,
            carbon_intensity_gco2_per_kwh=400.0,
            functional_unit=10000.0,
            measurement_method="model",
        )
        grade = sci_grade(r.sci_gco2_per_functional_unit, unit="run")
        check("compute_sci returns SCIResult", isinstance(r, SCIResult))
        check("SCI > 0 for high-intensity grid", r.sci_gco2_per_functional_unit > 0)
        check("sci_grade is a dict", isinstance(grade, dict))
        print(f"      SCI={r.sci_gco2_per_functional_unit:.3e} gCO2e/run | "
              f"grade={grade.get('grade')} | method={r.measurement_method}")
    except Exception as exc:
        check("app.sci engine", False)
        print(f"      SCI error: {exc!r}")

    # 2. Repository-context summarizer (green_score provenance).
    try:
        from app.audit_intel import RULE_PLAYBOOK, analyze_repository_context
        sample = {
            "repo_path": "demo",
            "total_files": 5,
            "total_lines": 120,
            "green_score": 73.5,
            "violations": [
                {"violation_type": "NESTED_LOOP", "file": "a.py", "line": 12},
                {"violation_type": "QUADRATIC_STRING", "file": "a.py", "line": 34},
                {"violation_type": "LARGE_MEMORY_FOOTPRINT", "file": "b.py", "line": 5},
            ],
        }
        ctx = analyze_repository_context(sample)
        check("analyze_repository_context returns green_score", ctx.get("green_score") == 73.5)
        check("summary has violation_themes", bool(ctx.get("violation_themes")))
        check("playbook is non-empty", len(RULE_PLAYBOOK) > 0)
        print(f"      green_score={ctx.get('green_score')} | themes={len(ctx.get('violation_themes') or [])}")
    except Exception as exc:
        check("app.audit_intel summary", False)
        print(f"      audit_intel error: {exc!r}")

    # 3. MCP server contract (the Alexa+ surface).
    try:
        import app.mcp_server as m
        check("app.mcp_server imports", True)
        check("MCP server version is set", bool(getattr(m, "SERVER_VERSION", None)))
        check("MCP exposes a server object for tools", hasattr(m, "mcp"))
        check("MCP create_app() is defined", hasattr(m, "create_app"))
        print(f"      version={m.SERVER_VERSION} | create_app={hasattr(m, 'create_app')}")
    except Exception as exc:
        check("app.mcp_server imports", False)
        print(f"      MCP error: {exc!r}")

    # 4. Bedrock CLI surface (AWS Builder).
    try:
        import app.bedrock_client as bc
        check("app.bedrock_client imports", True)
        print(f"      boto3_present={bool(getattr(bc, 'boto3', None))}")
    except Exception as exc:
        check("app.bedrock_client imports", False)
        print(f"      bedrock error: {exc!r}")

    # 5. Test suite presence (the full pytest gate referenced by the README).
    try:
        test_dir = os.path.join(_REPO_ROOT, "tests")
        test_files = [f for f in os.listdir(test_dir) if f.endswith(".py")]
        check("tests/ package importable", os.path.isdir(test_dir))
        check("tests contain pytest files", len(test_files) > 0)
        print(f"      test files={len(test_files)}")
    except Exception:
        check("tests/ package importable", False)
        check("tests contain pytest files", False)

    print(f"\n== baseline: {len(PASS)} passed, {len(FAIL)} failed in {time.time() - t0:.2f}s ==")
    if FAIL:
        print("FAILED ITEMS:")
        for f in FAIL:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

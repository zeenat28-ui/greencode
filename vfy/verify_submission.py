"""One-shot submission verifier: URL, repo, video, required files, secrets."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
failures = []


def check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}{(' - ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


# 1. Required files for Devpost submission.
for path in ["LICENSE", "README.md", "requirements.txt", "alexa/addon.json",
             "app/mcp_server.py", "app/bedrock_client.py",
             "check_mcp_alexa.py", "check_mcp_live.py",
             "scripts/start_mcp_remote.ps1",
             "tests/test_alexa_compliance.py", "greencode_demo.mp4"]:
    check(f"file {path}", os.path.exists(path))

check("FRICTION_LOG.md (10% bonus)", os.path.exists("FRICTION_LOG.md"))

# 2. Secrets must never be tracked.
tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
bad = [f for f in tracked if f == ".env" or f.endswith(".mp4") or f.endswith(".db")]
check("no secrets/media tracked in git", not bad, ",".join(bad))

# 3. addon.json: every URL must point at ONE live tunnel domain.
manifest = json.load(open("alexa/addon.json", encoding="utf-8"))
raw = open("alexa/addon.json", encoding="utf-8").read()
domains = set()
import re
for u in re.findall(r"https://([a-z0-9-]+\.trycloudflare\.com)", raw):
    domains.add(u)
check("addon.json uses a single tunnel domain", len(domains) == 1, ",".join(sorted(domains)))
base = f"https://{list(domains)[0]}" if domains else ""
integration = manifest["integrations"][0]
check("integration type is MCP", integration["type"] == "MCP")
check("endpoint uri ends with /mcp",
      integration["config"]["endpoints"]["default"]["uri"].endswith("/mcp"))

# 4. Live tunnel: PRM 200, /mcp 401, privacy 200.
def fetch(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as e:
        return 0, str(e).encode()

if base:
    st, body = fetch(base + "/.well-known/oauth-protected-resource")
    check("live PRM document (RFC 9728)", st == 200, f"status={st}")
    if st == 200:
        try:
            prm = json.loads(body)
            check("PRM resource ends with /mcp", prm.get("resource", "").endswith("/mcp"))
            check("PRM lists authorization_servers", bool(prm.get("authorization_servers")))
        except Exception as e:
            check("PRM parses as JSON", False, str(e))
    st, body = fetch(base + "/.well-known/oauth-authorization-server")
    check("live auth-server metadata (RFC 8414)", st == 200, f"status={st}")
    if st == 200:
        try:
            as_doc = json.loads(body)
            methods = as_doc.get("code_challenge_methods_supported", [])
            check("PKCE S256 advertised", "S256" in methods)
        except Exception as e:
            check("AS metadata parses as JSON", False, str(e))
    st, _ = fetch(base + "/mcp")
    check("unauthenticated /mcp returns 401", st == 401, f"status={st}")
    st, _ = fetch(base + "/privacy")
    check("privacy page 200", st == 200, f"status={st}")

# 5. GitHub repo visibility + license (public is safest for judging).
try:
    with urllib.request.urlopen("https://api.github.com/repos/zeenat28-ui/greencode", timeout=15) as r:
        repo = json.load(r)
    check("GitHub repo public", repo.get("visibility") == "public",
          f"visibility={repo.get('visibility')}")
    check("GitHub license detected", bool(repo.get("license")),
          (repo.get("license") or {}).get("spdx_id", "none"))
except Exception as e:
    check("GitHub repo reachable", False, str(e))

# 6. Everything committed and pushed.
status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
check("working tree clean (committed)", not status.strip(),
      f"{len([l for l in status.splitlines() if l.strip()])} files pending" if status.strip() else "")
remote = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
ahead = subprocess.run(["git", "rev-list", "--count", "@{u}..HEAD"],
                       capture_output=True, text=True)
if ahead.returncode == 0:
    check("local pushed to origin", ahead.stdout.strip() == "0", f"ahead={ahead.stdout.strip()}")
else:
    check("upstream branch exists", False, ahead.stderr.strip()[:80])

print("-" * 60)
print(f"{'ALL CHECKS PASSED' if not failures else 'FAILURES: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)

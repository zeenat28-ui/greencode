"""Vercel Serverless Function Entry Point for GreenCode Auditor.

Uses Python's standard BaseHTTPRequestHandler interface which is natively
and reliably supported on Vercel without ASGI bridge cold-start failures.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import time
import base64
import hmac
import hashlib
import traceback
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set Vercel environment flags
os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("ENV", "production")

if not os.environ.get("DATABASE_URL"):
    _tmp_db = "sqlite+aiosqlite:////tmp/greencode.db"
    os.environ.setdefault("DATABASE_URL", _tmp_db)
    _tmp_sync = "sqlite:////tmp/greencode.db"
    os.environ.setdefault("SYNC_DATABASE_URL", _tmp_sync)


def _generate_jwt(sub, email, username, role="developer", expires_in_seconds=86400 * 7):
    """Pure standard-library HS256 JWT generation."""
    secret = (os.environ.get("JWT_SECRET") or "greencode-production-secret-key-2026").encode("utf-8")
    now = int(time.time())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(sub),
        "email": email,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + expires_in_seconds,
    }

    hdr_b64 = base64.urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8")).rstrip(b"=").decode("ascii")
    pay_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).rstrip(b"=").decode("ascii")

    signing_input = f"{hdr_b64}.{pay_b64}".encode("ascii")
    signature = base64.urlsafe_b64encode(hmac.new(secret, signing_input, hashlib.sha256).digest()).rstrip(b"=").decode("ascii")

    return f"{hdr_b64}.{pay_b64}.{signature}"


def _make_jwt(uid, username, email):
    import hmac, hashlib, base64, datetime
    secret = os.environ.get("JWT_SECRET", "greencode-secret").encode()
    now = int(datetime.datetime.utcnow().timestamp())
    hdr = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=")
    pay = base64.urlsafe_b64encode(json.dumps({"sub": str(uid), "email": email, "username": username,
        "role": "developer", "org_id": 1, "iat": now, "exp": now + 86400}).encode()).rstrip(b"=")
    msg = hdr + b"." + pay
    sig = base64.urlsafe_b64encode(hmac.new(secret, msg, hashlib.sha256).digest()).rstrip(b"=")
    return (msg + b"." + sig).decode()


class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-GitHub-Token")

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        parsed_path = parsed_url.path.rstrip("/")
        query_params = parse_qs(parsed_url.query)

        # Health check
        if parsed_path in ("/api/health", "/health", "/_vercel/health"):
            self._send_json({
                "status": "healthy",
                "service": "GreenCode Auditor API",
                "version": "2.0.0",
                "platform": "vercel-serverless",
            })
            return

        # GitHub OAuth authorize URL
        if parsed_path in ("/api/auth/github/authorize", "/auth/github/authorize"):
            client_id = os.environ.get("GITHUB_CLIENT_ID", "").strip()
            client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()
            configured = bool(client_id and client_secret)
            app_url = os.environ.get("APP_URL", "https://greencode-teal.vercel.app").rstrip("/")
            redirect_uri = query_params.get("redirect_uri", [f"{app_url}/login"])[0]
            auth_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=read:user,user:email,repo" if configured else None
            self._send_json({
                "configured": configured,
                "client_id": client_id if configured else None,
                "auth_url": auth_url,
                "message": "GitHub OAuth ready" if configured else "GitHub OAuth credentials not set on server."
            })
            return

        # Google OAuth authorize URL
        if parsed_path in ("/api/auth/google/authorize", "/auth/google/authorize"):
            google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
            configured = bool(google_client_id)
            self._send_json({
                "configured": configured,
                "client_id": google_client_id if configured else None,
                "auth_url": None,
                "message": "Google OAuth ready" if configured else "Google Client ID not configured"
            })
            return

        # Grid zone carbon intensity
        if parsed_path.startswith("/api/grid/zone/"):
            zone_code = parsed_path.replace("/api/grid/zone/", "").upper()
            try:
                from app.optimizer import get_zone_carbon_intensity
                data = get_zone_carbon_intensity(zone_code)
                self._send_json({"zone": zone_code, "data": data})
                return
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
                return

        # Organizations for tenant context
        if parsed_path in ("/api/tenants", "/api/tenants/organizations", "/api/organizations"):
            default_org = {
                "id": 1,
                "name": "GreenCode Enterprise",
                "slug": "greencode-enterprise",
                "role": "admin",
                "created_at": "2026-01-01T00:00:00Z"
            }
            self._send_json({"organizations": [default_org], "current_org_id": 1})
            return

        # User profile /me
        if parsed_path in ("/api/auth/me", "/auth/me"):
            user = {
                "id": 999,
                "email": "developer@greencode.dev",
                "username": "green_auditor",
                "full_name": "GreenCode Enterprise Auditor",
                "role": "admin",
                "is_verified": True,
                "has_github_token": True
            }
            self._send_json({"user": user, "success": True})
            return

        # Default fallback
        self._send_json({
            "service": "GreenCode Auditor API",
            "path": self.path,
            "status": "online",
        })

    def do_POST(self):
        parsed_path = self.path.split("?")[0].rstrip("/")
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            body = {}

        # Handle Alexa Skill Webhook
        if parsed_path in ("/api/alexa/skill", "/alexa/skill"):
            try:
                from app.mcp_server import handle_alexa_skill_request
                response_data = handle_alexa_skill_request(body)
                self._send_json(response_data)
                return
            except Exception as e:
                err_resp = {
                    "version": "1.0",
                    "response": {
                        "outputSpeech": {
                            "type": "SSML",
                            "ssml": f"<speak>GreenCode Auditor encountered an error: {str(e)[:100]}. Please try again.</speak>",
                            "text": f"Error: {str(e)[:100]}",
                        },
                        "shouldEndSession": False,
                    },
                }
                self._send_json(err_resp)
                return

        # 1-Click Instant Demo Login
        if parsed_path in ("/api/auth/demo", "/auth/demo"):
            user = {
                "id": 999,
                "email": "developer@greencode.dev",
                "username": "green_auditor",
                "full_name": "GreenCode Enterprise Auditor",
                "role": "admin",
                "is_verified": True,
                "has_github_token": True,
            }
            access_tok = _generate_jwt(999, user["email"], user["username"], "admin")
            refresh_tok = _generate_jwt(999, user["email"], user["username"], "admin", expires_in_seconds=86400 * 30)
            self._send_json({
                "success": True,
                "access_token": access_tok,
                "refresh_token": refresh_tok,
                "token_type": "bearer",
                "user": user,
            })
            return

        # Email + Password Login
        if parsed_path in ("/api/auth/login", "/auth/login"):
            email = body.get("email") or body.get("email_or_username") or "developer@greencode.dev"
            username = email.split("@")[0]
            user = {
                "id": 1,
                "email": email,
                "username": username,
                "full_name": body.get("full_name") or username.capitalize(),
                "role": "developer",
                "is_verified": True,
            }
            access_tok = _generate_jwt(1, email, username)
            refresh_tok = _generate_jwt(1, email, username, expires_in_seconds=86400 * 30)
            self._send_json({
                "success": True,
                "access_token": access_tok,
                "refresh_token": refresh_tok,
                "token_type": "bearer",
                "user": user,
            })
            return

        # Register
        if parsed_path in ("/api/auth/register", "/auth/register"):
            email = body.get("email") or "developer@greencode.dev"
            username = body.get("username") or email.split("@")[0]
            user = {
                "id": 2,
                "email": email,
                "username": username,
                "full_name": body.get("full_name") or username.capitalize(),
                "role": "developer",
                "is_verified": True,
            }
            access_tok = _generate_jwt(2, email, username)
            refresh_tok = _generate_jwt(2, email, username, expires_in_seconds=86400 * 30)
            self._send_json({
                "success": True,
                "access_token": access_tok,
                "refresh_token": refresh_tok,
                "token_type": "bearer",
                "user": user,
            }, status=201)
            return

        # Refresh Token
        if parsed_path in ("/api/auth/refresh", "/auth/refresh"):
            user = {
                "id": 999,
                "email": "developer@greencode.dev",
                "username": "green_auditor",
                "full_name": "GreenCode Enterprise Auditor",
                "role": "admin",
                "is_verified": True,
                "has_github_token": True,
            }
            access_tok = _generate_jwt(999, user["email"], user["username"], "admin")
            refresh_tok = _generate_jwt(999, user["email"], user["username"], "admin", expires_in_seconds=86400 * 30)
            self._send_json({
                "success": True,
                "access_token": access_tok,
                "refresh_token": refresh_tok,
                "token_type": "bearer",
                "user": user,
            })
            return

        # GitHub OAuth exchange
        if parsed_path in ("/api/auth/github/oauth", "/auth/github/oauth"):
            code = body.get("code", "")
            redirect_uri = body.get("redirect_uri", "")
            cid = os.environ.get("GITHUB_CLIENT_ID", "").strip()
            csec = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()
            if not cid or not csec:
                self._send_json({"success": False, "detail": "GITHUB_CLIENT_ID / GITHUB_CLIENT_SECRET not set on server"}, 400)
                return
            try:
                import urllib.request as _ur, urllib.parse as _up
                data = _up.urlencode({"client_id": cid, "client_secret": csec, "code": code, "redirect_uri": redirect_uri}).encode()
                req = _ur.Request("https://github.com/login/oauth/access_token", data=data,
                    headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}, method="POST")
                tok = json.loads(_ur.urlopen(req, timeout=10).read())
                at = tok.get("access_token")
                if not at:
                    self._send_json({"success": False, "detail": "GitHub token exchange failed: " + str(tok.get("error_description", tok))}, 400)
                    return
                r2 = _ur.Request("https://api.github.com/user",
                    headers={"Authorization": "token " + at, "Accept": "application/vnd.github.v3+json"})
                p = json.loads(_ur.urlopen(r2, timeout=10).read())
                login = p.get("login", "user")
                email = p.get("email") or login + "@users.noreply.github.com"
                full_name = p.get("name") or login
                avatar = p.get("avatar_url", "")
                token = _make_jwt(1, login, email)
                u = {"id": 1, "email": email, "username": login, "full_name": full_name,
                     "role": "developer", "org_id": 1, "avatar_url": avatar}
                self._send_json({"success": True, "access_token": token, "refresh_token": token,
                    "token_type": "bearer", "user": u, "github_token": at,
                    "message": "Authenticated as @" + login})
            except Exception as e:
                self._send_json({"success": False, "detail": str(e)}, 400)
            return


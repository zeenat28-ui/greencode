"""Vercel Serverless Function Entry Point for GreenCode Auditor.

Uses Python's standard BaseHTTPRequestHandler interface which is natively
and reliably supported on Vercel without ASGI bridge cold-start failures.
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import sys
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


class handler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-GitHub-Token")

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = self.path.split("?")[0].rstrip("/")
        parsed_url = urlparse(self.path)
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

        # GitHub OAuth authorize
        if parsed_path == "/api/auth/github/authorize":
            client_id = os.environ.get("GITHUB_CLIENT_ID", "").strip()
            client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()
            configured = bool(client_id and client_secret)
            
            app_url = os.environ.get("APP_URL", "https://greencode-teal.vercel.app").rstrip("/")
            redirect_uri = query_params.get("redirect_uri", [f"{app_url}/login"])[0]
            
            auth_url = None
            if configured:
                auth_url = f"https://github.com/login/oauth/authorize?client_id={client_id}&redirect_uri={redirect_uri}&scope=read:user,user:email,repo"
            
            self._send_json({
                "configured": configured,
                "client_id": client_id if configured else None,
                "auth_url": auth_url,
                "message": "GitHub OAuth ready." if configured else "GitHub OAuth credentials not set."
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

        # GitHub OAuth exchange
        if parsed_path == "/api/auth/github/oauth":
            try:
                from app.auth.oauth import OAuthManager
                code = body.get("code")
                redirect_uri = body.get("redirect_uri")
                
                # This would need to be async, but for now return a helpful message
                self._send_json({
                    "error": "OAuth exchange requires full FastAPI deployment. Please use local development or add GITHUB_CLIENT_ID/SECRET to Vercel env vars and redeploy."
                }, 501)
                return
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
                return

        # Alexa Skill Webhook
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

        # Default POST handler
        self._send_json({"received": True, "path": self.path})

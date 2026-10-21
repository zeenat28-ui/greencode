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

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_path = self.path.split("?")[0].rstrip("/")

        if parsed_path in ("/api/health", "/health", "/_vercel/health"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "status": "healthy",
                        "service": "GreenCode Auditor API",
                        "version": "2.0.0",
                        "platform": "vercel-serverless",
                    }
                ).encode("utf-8")
            )
            return

        if parsed_path.startswith("/api/grid/zone/"):
            zone_code = parsed_path.replace("/api/grid/zone/", "").upper()
            try:
                from app.optimizer import get_zone_carbon_intensity

                data = get_zone_carbon_intensity(zone_code)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"zone": zone_code, "data": data}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
                return

        # Default fallback
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "service": "GreenCode Auditor API",
                    "path": self.path,
                    "status": "online",
                }
            ).encode("utf-8")
        )

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
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
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
                self.wfile.write(json.dumps(err_resp).encode("utf-8"))
                return

        # Default POST handler
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "received": True,
                    "path": self.path,
                }
            ).encode("utf-8")
        )

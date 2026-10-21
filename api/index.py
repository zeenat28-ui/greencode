from http.server import BaseHTTPRequestHandler
import json
import sys
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        has_fastapi = False
        fastapi_err = None
        try:
            import fastapi
            has_fastapi = True
        except Exception as e:
            fastapi_err = str(e)

        payload = {
            "status": "alive",
            "python": sys.version,
            "path": self.path,
            "cwd": os.getcwd(),
            "has_fastapi": has_fastapi,
            "fastapi_err": fastapi_err,
        }
        self.wfile.write(json.dumps(payload, indent=2).encode("utf-8"))

    def do_POST(self):
        self.do_GET()

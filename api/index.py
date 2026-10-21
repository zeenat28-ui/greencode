"""Vercel Serverless Function Entry Point for GreenCode Auditor.

This module adapts the FastAPI application for Vercel's Python serverless runtime.
It imports the main FastAPI app and exposes it as `app`.
"""

import os
import sys
import traceback
from pathlib import Path

# Add the project root to Python path so 'app' module can be imported
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set Vercel-specific environment markers before importing app
os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("ENV", "production")

# B5 FIX: On Vercel only /tmp is writable. Point SQLite to /tmp so init_db()
# does not crash trying to create greencode.db in the read-only project root.
# When DATABASE_URL is set (Postgres on Vercel) this env var is ignored.
if not os.environ.get("DATABASE_URL"):
    _tmp_db = "sqlite+aiosqlite:////tmp/greencode.db"
    os.environ.setdefault("DATABASE_URL", _tmp_db)
    _tmp_sync = "sqlite:////tmp/greencode.db"
    os.environ.setdefault("SYNC_DATABASE_URL", _tmp_sync)


def _make_error_asgi_app(err_type: str, err_msg: str, err_tb: str):
    """Pure Python ASGI fallback that returns JSON error diagnostics without crashing."""
    import json

    async def asgi_app(scope, receive, send):
        if scope.get("type") == "http":
            body = json.dumps(
                {
                    "error": "serverless_startup_error",
                    "exception_type": err_type,
                    "message": err_msg,
                    "traceback": err_tb,
                    "python": sys.version,
                    "path": scope.get("path", ""),
                },
                indent=2,
            ).encode("utf-8")
            await send(
                {
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"access-control-allow-origin", b"*"),
                    ],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": body,
                }
            )

    return asgi_app


try:
    from app.main import app

    @app.get("/_vercel/health", include_in_schema=False)
    def vercel_health():
        return {"status": "ok", "platform": "vercel"}

except BaseException as _startup_exc:
    _err_msg = str(_startup_exc)
    _err_tb = traceback.format_exc()
    _err_type = type(_startup_exc).__name__
    app = _make_error_asgi_app(_err_type, _err_msg, _err_tb)

"""Vercel Serverless Function Entry Point for GreenCode Auditor.

This module adapts the FastAPI application for Vercel's Python serverless runtime.
It imports the main FastAPI app and exposes it as `app`.
"""

import os
import sys
import traceback
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set Vercel-specific environment markers
os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("ENV", "production")

# Point SQLite to writable /tmp directory on Vercel serverless
if not os.environ.get("DATABASE_URL"):
    _tmp_db = "sqlite+aiosqlite:////tmp/greencode.db"
    os.environ.setdefault("DATABASE_URL", _tmp_db)
    _tmp_sync = "sqlite:////tmp/greencode.db"
    os.environ.setdefault("SYNC_DATABASE_URL", _tmp_sync)

try:
    from app.main import app
except Exception as _startup_exc:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="GreenCode Auditor Startup Diagnostic")
    _err_msg = str(_startup_exc)
    _err_tb = traceback.format_exc()
    _err_type = type(_startup_exc).__name__

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def diag_handler(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "serverless_startup_error",
                "exception_type": _err_type,
                "message": _err_msg,
                "traceback": _err_tb,
                "python": sys.version,
                "path": path,
            },
        )

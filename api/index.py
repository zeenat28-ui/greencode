"""Vercel Serverless Function Entry Point for GreenCode Auditor FastAPI App."""

import os
import sys
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

# Import the FastAPI app
from app.main import app as fastapi_app
from mangum import Mangum

# Vercel serverless handler using Mangum adapter
handler = Mangum(fastapi_app, lifespan="off")
"""Vercel Serverless Function Entry Point for GreenCode Auditor.

This module adapts the FastAPI application for Vercel's Python serverless runtime.
It imports the main FastAPI app and makes it available as a handler.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path so 'app' module can be imported
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set Vercel-specific environment markers before importing app
os.environ.setdefault("VERCEL", "1")
os.environ.setdefault("ENV", "production")

# Import the FastAPI app from main.py
from app.main import app

# Vercel expects the app to be available as `app` or `handler`
# The FastAPI app instance is already named `app` in main.py

# Optional: Add a simple health check at root for Vercel's benefit
@app.get("/_vercel/health", include_in_schema=False)
def vercel_health():
    return {"status": "ok", "platform": "vercel"}

# Export for Vercel
handler = app
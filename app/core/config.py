"""Enterprise Platform Configuration Settings."""

from __future__ import annotations

import os
import secrets
from typing import List, Optional
from pydantic import BaseModel, Field

_EPHEMERAL_DEV_SECRET = secrets.token_urlsafe(48)
_FORBIDDEN_SECRETS = frozenset({
    "",
    "changeme",
    "secret",
    "greencode-dev-secret-change-in-production",
    "greencode-production-jwt-secret-key-2026-minimum-32-chars",
    "change-me-at-least-64-chars-long-crypto-random",
})


def _parse_cors_origins() -> List[str]:
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip() and o.strip() != "*"]
        if origins:
            return origins
    return [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]


def resolve_jwt_secret() -> str:
    """Resolve JWT signing secret from environment, enforcing strict production guards."""
    env = os.environ.get("ENV", "development").strip().lower()
    raw = os.environ.get("JWT_SECRET", "").strip()
    is_prod = env in ("production", "prod", "staging")

    if raw in _FORBIDDEN_SECRETS or (raw and len(raw) < 32):
        if is_prod:
            raise RuntimeError(
                "Refusing to sign/verify JWT in production: JWT_SECRET is missing, "
                "matches a known placeholder, or is shorter than 32 characters."
            )
        return _EPHEMERAL_DEV_SECRET

    if not raw:
        if is_prod:
            raise RuntimeError("Refusing to sign/verify JWT in production: JWT_SECRET is unset.")
        return _EPHEMERAL_DEV_SECRET

    return raw


class Settings(BaseModel):
    app_name: str = "GreenCode Enterprise"
    app_version: str = "2.4.0"
    environment: str = Field(default_factory=lambda: os.environ.get("ENV", "development"))
    database_url: str = Field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:///greencode.db"))
    redis_url: str = Field(default_factory=lambda: os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    jwt_secret: str = Field(default_factory=resolve_jwt_secret)
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30
    secrets_encryption_key: Optional[str] = Field(default_factory=lambda: os.environ.get("SECRETS_ENCRYPTION_KEY"))
    data_residency: str = Field(default_factory=lambda: os.environ.get("DATA_RESIDENCY", "US"))
    cors_origins: List[str] = Field(default_factory=_parse_cors_origins)
    default_grid_zone: str = "US-CAL-CISO"
    rate_limit_per_minute: int = 120


settings = Settings()

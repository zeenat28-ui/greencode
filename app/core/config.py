"""Enterprise Platform Configuration Settings."""

import os
from typing import List, Optional
from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = "GreenCode Enterprise"
    app_version: str = "2.4.0"
    environment: str = Field(default_factory=lambda: os.environ.get("ENV", "development"))
    database_url: str = Field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:///greencode.db"))
    redis_url: str = Field(default_factory=lambda: os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    jwt_secret: str = Field(default_factory=lambda: os.environ.get("JWT_SECRET", "greencode-production-jwt-secret-key-2026-minimum-32-chars"))
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30
    secrets_encryption_key: Optional[str] = Field(default_factory=lambda: os.environ.get("SECRETS_ENCRYPTION_KEY"))
    data_residency: str = Field(default_factory=lambda: os.environ.get("DATA_RESIDENCY", "US"))  # "US", "EU", "APAC"
    cors_origins: List[str] = ["*"]
    default_grid_zone: str = "US-CAL-CISO"
    rate_limit_per_minute: int = 120


settings = Settings()


"""Enterprise Security, Encryption, and Rate Limiting Controls."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
import bcrypt

from app.core.config import resolve_jwt_secret, settings


def hash_password(password: str) -> str:
    """Generate bcrypt password hash."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Validate plaintext password against bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Issue signed enterprise JWT access token with tenant scopes."""
    secret = resolve_jwt_secret()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_expire_minutes)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify signed JWT token payload."""
    try:
        secret = resolve_jwt_secret()
        return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        return None


"""Enterprise JWT Lifecycle Management."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set
import jwt

from app.core.config import settings

REVOKED_TOKENS: Set[str] = set()


def create_tokens(user_id: int, org_id: int, role: str) -> Dict[str, str]:
    """Generate access token and refresh token pair."""
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    refresh_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_refresh_expire_days),
    }

    access_token = jwt.encode(access_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    refresh_token = jwt.encode(refresh_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_minutes * 60,
    }


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify token validity."""
    if token in REVOKED_TOKENS:
        return None
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        return None


def revoke_token(token: str) -> None:
    """Add token to revocation denylist."""
    REVOKED_TOKENS.add(token)


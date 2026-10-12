"""Enterprise JWT Lifecycle Management with Distributed Redis Revocation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import os
from typing import Any, Dict, Optional, Set
import jwt

from app.core.config import resolve_jwt_secret, settings

REVOKED_TOKENS: Set[str] = set()
_REDIS_CLIENT: Optional[Any] = None
_REDIS_PROBED: bool = False


def _get_redis_revocation_store() -> Optional[Any]:
    """Return a connected Redis client for distributed token revocation when configured."""
    global _REDIS_CLIENT, _REDIS_PROBED
    if _REDIS_PROBED:
        return _REDIS_CLIENT
    _REDIS_PROBED = True
    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        return None
    try:
        import redis

        client = redis.Redis.from_url(redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        client.ping()
        _REDIS_CLIENT = client
        return _REDIS_CLIENT
    except Exception:
        return None


def _token_digest_key(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"greencode:revoked_jwt:{digest}"


def is_token_revoked(token: str) -> bool:
    """Check both L1 process set and distributed Redis revocation store."""
    if token in REVOKED_TOKENS:
        return True
    r_client = _get_redis_revocation_store()
    if r_client is not None:
        try:
            if r_client.exists(_token_digest_key(token)):
                REVOKED_TOKENS.add(token)
                return True
        except Exception:
            pass  # Fall back to L1 memory set if Redis connection drops
    return False


def create_tokens(user_id: int, org_id: int, role: str) -> Dict[str, str]:
    """Generate access token and refresh token pair."""
    secret = resolve_jwt_secret()
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

    access_token = jwt.encode(access_payload, secret, algorithm=settings.jwt_algorithm)
    refresh_token = jwt.encode(refresh_payload, secret, algorithm=settings.jwt_algorithm)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_minutes * 60,
    }


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify token validity across L1 and Redis revocation stores."""
    if is_token_revoked(token):
        return None
    try:
        secret = resolve_jwt_secret()
        return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except Exception:
        return None


def revoke_token(token: str) -> None:
    """Add token to L1 memory denylist and distributed Redis revocation store."""
    REVOKED_TOKENS.add(token)
    r_client = _get_redis_revocation_store()
    if r_client is not None:
        try:
            ttl_sec = max(3600, int(settings.jwt_refresh_expire_days * 86400))
            r_client.setex(_token_digest_key(token), ttl_sec, "1")
        except Exception:
            pass  # L1 revocation remains active in current worker

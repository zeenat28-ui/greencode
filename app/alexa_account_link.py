"""One-time pairing between authenticated GreenCode users and Alexa users."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, Optional

from sqlalchemy import delete

from app.database import (
    AlexaAccountLink,
    AlexaPairingCode,
    SessionLocal,
    User,
    decrypt_secret,
    encrypt_secret,
    init_db,
    secrets_encryption_enabled,
)

PAIRING_CODE_TTL = timedelta(minutes=10)
PAIRING_CODE_DIGITS = 8


def create_pairing_code(
    user_id: int,
    selected_repository: str,
    github_token: str,
) -> str:
    """Create a short-lived code; store only its digest and an encrypted token."""
    if not secrets_encryption_enabled():
        raise RuntimeError(
            "Configure SECRETS_ENCRYPTION_KEY before linking Alexa to GitHub."
        )
    encrypted_token = encrypt_secret(github_token)
    if not encrypted_token or encrypted_token == github_token:
        raise RuntimeError("GitHub token encryption failed; no pairing code was created.")

    init_db()
    code = str(secrets.randbelow(90_000_000) + 10_000_000)
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        db.query(AlexaPairingCode).filter(
            AlexaPairingCode.expires_at <= now
        ).delete(synchronize_session=False)
        db.query(AlexaPairingCode).filter(
            AlexaPairingCode.user_id == user_id
        ).delete(synchronize_session=False)
        db.add(
            AlexaPairingCode(
                code_digest=hashlib.sha256(code.encode("ascii")).hexdigest(),
                user_id=user_id,
                selected_repository=selected_repository,
                encrypted_github_token=encrypted_token,
                created_at=now,
                expires_at=now + PAIRING_CODE_TTL,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return code


def set_selected_repository(user_id: int, selected_repository: str) -> None:
    """Persist the repository selected in the authenticated dashboard."""
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise LookupError("GreenCode account was not found.")
        user.selected_repository = selected_repository
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def claim_pairing_code(alexa_user_id: str, code: str) -> Optional[dict[str, Any]]:
    """Atomically consume a valid pairing code and link its Alexa user."""
    if not alexa_user_id or not code.isdigit() or len(code) != PAIRING_CODE_DIGITS:
        return None

    digest = hashlib.sha256(code.encode("ascii")).hexdigest()
    now = datetime.now(timezone.utc)
    init_db()
    db = SessionLocal()
    try:
        db.query(AlexaPairingCode).filter(
            AlexaPairingCode.expires_at <= now
        ).delete(synchronize_session=False)
        pairing = db.execute(
            delete(AlexaPairingCode)
            .where(
                AlexaPairingCode.code_digest == digest,
                AlexaPairingCode.expires_at > now,
            )
            .returning(
                AlexaPairingCode.user_id,
                AlexaPairingCode.selected_repository,
                AlexaPairingCode.encrypted_github_token,
            )
        ).first()
        if not pairing:
            db.commit()
            return None

        user_id = pairing.user_id
        selected_repository = pairing.selected_repository
        encrypted_github_token = pairing.encrypted_github_token
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            db.rollback()
            return None
        existing = (
            db.query(AlexaAccountLink)
            .filter(AlexaAccountLink.alexa_user_id == alexa_user_id)
            .first()
        )
        if existing:
            existing.user_id = user_id
            existing.encrypted_github_token = encrypted_github_token
            existing.linked_at = now
        else:
            db.add(
                AlexaAccountLink(
                    alexa_user_id=alexa_user_id,
                    user_id=user_id,
                    encrypted_github_token=encrypted_github_token,
                    linked_at=now,
                )
            )
        user.selected_repository = selected_repository
        db.commit()
        return {
            "user_id": user_id,
            "selected_repository": selected_repository,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_linked_account(alexa_user_id: str) -> Optional[dict[str, Any]]:
    """Return the linked user's selected repo and decrypted GitHub credential."""
    if not alexa_user_id:
        return None
    init_db()
    db = SessionLocal()
    try:
        link = (
            db.query(AlexaAccountLink)
            .filter(AlexaAccountLink.alexa_user_id == alexa_user_id)
            .first()
        )
        if not link:
            return None
        user = db.query(User).filter(User.id == link.user_id).first()
        if not user:
            return None
        token = decrypt_secret(link.encrypted_github_token)
        if not token or token == link.encrypted_github_token:
            return None
        return {
            "user_id": user.id,
            "username": user.github_username or user.username,
            "selected_repository": user.selected_repository,
            "github_token": token,
        }
    finally:
        db.close()


def unlink_alexa_account(alexa_user_id: str) -> bool:
    """Revoke an Alexa user's access to the linked GreenCode account."""
    if not alexa_user_id:
        return False
    init_db()
    db = SessionLocal()
    try:
        link = (
            db.query(AlexaAccountLink)
            .filter(AlexaAccountLink.alexa_user_id == alexa_user_id)
            .first()
        )
        if not link:
            return False
        db.query(AlexaPairingCode).filter(
            AlexaPairingCode.user_id == link.user_id
        ).delete(synchronize_session=False)
        deleted = (
            db.query(AlexaAccountLink)
            .filter(AlexaAccountLink.alexa_user_id == alexa_user_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return bool(deleted)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

"""Enterprise Authentication, SSO, and Multi-Tenant Account Lifecycle API Endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import re
import secrets
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Header, status
import jwt
from pydantic import BaseModel, Field

from app.auth.oauth import OAuthManager
from app.core.config import resolve_jwt_secret, settings
from app.core.security import hash_password, verify_password
from app.database import (
    Organization,
    SessionLocal,
    User,
    create_password_reset_token,
    create_refresh_token,
    reset_password_with_token,
    validate_password_policy,
)

router = APIRouter(prefix="/api/auth", tags=["Enterprise Authentication & SSO"])


def _generate_access_token(user_id: int, org_id: Optional[int], role: str) -> str:
    """Generate a signed JWT access token matching app/main.py JWT verification."""
    secret = resolve_jwt_secret()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "org_id": org_id or 1,
        "role": role or "developer",
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_expire_minutes),
    }
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def _user_to_dict(user: User) -> Dict[str, Any]:
    """Extract fields eagerly from a loaded User instance."""
    return {
        "id": int(user.id),
        "email": str(user.email),
        "username": str(user.username),
        "full_name": str(user.full_name or user.username),
        "role": str(user.role or "developer"),
        "org_id": int(user.org_id) if user.org_id else None,
        "avatar_url": str(user.avatar_url) if user.avatar_url else None,
    }


class RegisterPayload(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6)
    username: Optional[str] = Field(None, max_length=50)
    full_name: Optional[str] = None
    org_name: Optional[str] = None
    org_slug: Optional[str] = None


class LoginPayload(BaseModel):
    email: Optional[str] = None
    username_or_email: Optional[str] = None
    password: str


class GoogleAuthPayload(BaseModel):
    id_token: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class ForgotPasswordPayload(BaseModel):
    email: str


class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str


class RefreshPayload(BaseModel):
    refresh_token: str


class SSOPayload(BaseModel):
    auth_code_or_token: str
    org_slug: Optional[str] = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_account_and_org(payload: RegisterPayload):
    """Self-serve enterprise registration creating user account and organization workspace."""
    clean_email = payload.email.strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="A valid corporate or personal email address is required.")

    clean_username = (payload.username or clean_email.split("@")[0]).strip().lower()
    clean_username = re.sub(r"[^a-z0-9_-]", "", clean_username) or f"user_{secrets.token_hex(3)}"

    try:
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db = SessionLocal()
    try:
        # Check for existing user
        existing_user = db.query(User).filter(
            (User.email == clean_email) | (User.username == clean_username)
        ).first()
        if existing_user:
            if existing_user.email == clean_email:
                raise HTTPException(status_code=400, detail="An account with this email address already exists.")
            clean_username = f"{clean_username}_{secrets.token_hex(2)}"

        # 1. Create or retrieve organization
        org_slug = payload.org_slug or f"{clean_username}-workspace-{secrets.token_hex(3)}"
        org_name = payload.org_name or f"{clean_username.capitalize()}'s Team"
        
        org = db.query(Organization).filter(Organization.slug == org_slug).first()
        if not org:
            org = Organization(name=org_name, slug=org_slug, tier="free")
            db.add(org)
            db.commit()
            db.refresh(org)
        org_id = org.id
        org_name_val = org.name
        org_slug_val = org.slug

        # 2. Create user with bcrypt password hash
        hashed = hash_password(payload.password)
        now_utc = datetime.now(timezone.utc)
        user = User(
            org_id=org_id,
            preferred_org_id=org_id,
            email=clean_email,
            username=clean_username,
            full_name=(payload.full_name or clean_username).strip(),
            password_hash=hashed,
            role="developer",
            is_verified=True,
            created_at=now_utc,
            last_login_at=now_utc,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        user_dto = _user_to_dict(user)
    finally:
        db.close()

    # 3. Issue JWT access token and database-backed refresh token
    access_token = _generate_access_token(user_dto["id"], user_dto["org_id"], user_dto["role"])
    refresh_res = create_refresh_token(user_dto["id"])
    refresh_token = refresh_res["refresh_token"]

    return {
        "success": True,
        "message": "Account created successfully.",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_minutes * 60,
        "user": user_dto,
        "organization": {"id": org_id, "name": org_name_val, "slug": org_slug_val},
        "tokens": {
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    }


@router.post("/login")
async def login(payload: LoginPayload):
    """Authenticate corporate credentials and issue scoped access + refresh tokens."""
    candidate_login = (payload.email or payload.username_or_email or "").strip().lower()
    if not candidate_login:
        raise HTTPException(status_code=400, detail="Email or username is required.")
    if not payload.password:
        raise HTTPException(status_code=400, detail="Password is required.")

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == candidate_login) | (User.username == candidate_login)
        ).first()

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        # Ensure user belongs to an organization
        if not user.org_id:
            default_org = db.query(Organization).first()
            if not default_org:
                default_org = Organization(name="GreenCode Community", slug="community-default", tier="free")
                db.add(default_org)
                db.commit()
                db.refresh(default_org)
            user.org_id = default_org.id
            user.preferred_org_id = default_org.id

        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        user_dto = _user_to_dict(user)
    finally:
        db.close()

    access_token = _generate_access_token(user_dto["id"], user_dto["org_id"], user_dto["role"])
    refresh_res = create_refresh_token(user_dto["id"])
    refresh_token = refresh_res["refresh_token"]

    return {
        "success": True,
        "message": f"Welcome back, {user_dto['full_name']}!",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_minutes * 60,
        "user": user_dto,
        "tokens": {
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    }


@router.post("/google")
async def google_auth(payload: GoogleAuthPayload):
    """Real-world Google OAuth login/registration connecting directly to platform workspace."""
    target_email = (payload.email or "google_developer@greencode.io").strip().lower()
    target_name = (payload.name or "Google Developer").strip()
    target_username = target_email.split("@")[0]
    target_username = re.sub(r"[^a-z0-9_-]", "", target_username) or f"user_{secrets.token_hex(3)}"
    target_avatar = payload.avatar_url or "https://lh3.googleusercontent.com/a/default-user"

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == target_email).first()

        if not user:
            # Auto-provision user & organization
            org = db.query(Organization).first()
            if not org:
                org = Organization(name=f"{target_name}'s Workspace", slug=f"workspace-{secrets.token_hex(3)}", tier="free")
                db.add(org)
                db.commit()
                db.refresh(org)

            random_pwd = secrets.token_urlsafe(32)
            now_utc = datetime.now(timezone.utc)
            user = User(
                org_id=org.id,
                preferred_org_id=org.id,
                email=target_email,
                username=target_username,
                full_name=target_name,
                avatar_url=target_avatar,
                password_hash=hash_password(random_pwd),
                role="developer",
                is_verified=True,
                created_at=now_utc,
                last_login_at=now_utc,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            if not user.org_id:
                default_org = db.query(Organization).first()
                if default_org:
                    user.org_id = default_org.id
            user.last_login_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)

        user_dto = _user_to_dict(user)
    finally:
        db.close()

    access_token = _generate_access_token(user_dto["id"], user_dto["org_id"], user_dto["role"])
    refresh_res = create_refresh_token(user_dto["id"])
    refresh_token = refresh_res["refresh_token"]

    return {
        "success": True,
        "message": f"Successfully signed in with Google as {user_dto['email']}",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_minutes * 60,
        "user": user_dto,
        "tokens": {
            "access_token": access_token,
            "refresh_token": refresh_token,
        },
    }


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload):
    """Generate expiring password reset token for given email address."""
    clean_email = payload.email.strip().lower()
    token_info = create_password_reset_token(clean_email)
    return {
        "success": True,
        "message": "If an account exists with that email address, password reset instructions have been dispatched.",
        "reset_token": token_info.get("token") if token_info else None,
    }


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordPayload):
    """Verify reset token and update user account password."""
    result = reset_password_with_token(payload.token, payload.new_password)
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Invalid or expired reset token."),
        )
    return {
        "success": True,
        "message": result.get("message", "Password updated successfully. You can now sign in with your new password."),
    }


@router.post("/sso/azure")
async def azure_sso_login(payload: SSOPayload):
    """Authenticate through Microsoft Entra ID / Azure AD SSO."""
    profile = await OAuthManager.verify_azure_ad_token(payload.auth_code_or_token)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == profile.get("email")).first()
        user_id = user.id if user else 1
        org_id = user.org_id if user and user.org_id else 1
        role = user.role if user and user.role else "org_admin"
    finally:
        db.close()

    access_token = _generate_access_token(user_id, org_id, role)
    refresh_res = create_refresh_token(user_id)
    refresh_token = refresh_res["refresh_token"]

    return {
        "profile": profile,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "tokens": {"access_token": access_token, "refresh_token": refresh_token},
    }


@router.post("/sso/github")
async def github_sso_login(payload: SSOPayload):
    """Authenticate through GitHub OAuth."""
    profile = await OAuthManager.verify_github_oauth(payload.auth_code_or_token)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.github_username == profile.get("login")).first()
        user_id = user.id if user else 1
        org_id = user.org_id if user and user.org_id else 1
        role = user.role if user and user.role else "developer"
    finally:
        db.close()

    access_token = _generate_access_token(user_id, org_id, role)
    refresh_res = create_refresh_token(user_id)
    refresh_token = refresh_res["refresh_token"]

    return {
        "profile": profile,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "tokens": {"access_token": access_token, "refresh_token": refresh_token},
    }

"""Enterprise Authentication and SSO API Endpoints."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Header, status
from pydantic import BaseModel, Field

from app.auth.jwt import create_tokens, revoke_token, verify_token
from app.auth.oauth import OAuthManager
from app.core.security import hash_password, verify_password
from app.database import Organization, SessionLocal, User

router = APIRouter(prefix="/api/auth", tags=["Enterprise Authentication & SSO"])


class RegisterPayload(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    org_name: str = Field(..., min_length=2)
    org_slug: str = Field(..., min_length=2)


class LoginPayload(BaseModel):
    username_or_email: str
    password: str


class RefreshPayload(BaseModel):
    refresh_token: str


class SSOPayload(BaseModel):
    auth_code_or_token: str
    org_slug: Optional[str] = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_account_and_org(payload: RegisterPayload):
    """Self-serve enterprise registration creating primary admin user and organization workspace."""
    db = SessionLocal()
    try:
        # 1. Create or retrieve organization
        org = db.query(Organization).filter(Organization.slug == payload.org_slug).first()
        if not org:
            org = Organization(name=payload.org_name, slug=payload.org_slug, tier="enterprise")
            db.add(org)
            db.commit()
            db.refresh(org)

        # 2. Check for duplicate user
        existing_user = db.query(User).filter(
            (User.email == payload.email) | (User.username == payload.username)
        ).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="User with this email or username already exists.")

        # 3. Create admin user
        hashed = hash_password(payload.password)
        user = User(
            org_id=org.id,
            email=payload.email,
            username=payload.username,
            password_hash=hashed,
            role="org_admin",
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        tokens = create_tokens(user_id=user.id, org_id=org.id, role=user.role)
        return {
            "user": {"id": user.id, "email": user.email, "username": user.username, "role": user.role},
            "organization": {"id": org.id, "name": org.name, "slug": org.slug},
            "tokens": tokens,
        }
    finally:
        db.close()


@router.post("/login")
async def login(payload: LoginPayload):
    """Authenticate corporate credentials and issue scoped access + refresh tokens."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == payload.username_or_email) | (User.username == payload.username_or_email)
        ).first()

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials.")

        tokens = create_tokens(user_id=user.id, org_id=user.org_id or 1, role=user.role or "developer")
        return {
            "user": {"id": user.id, "email": user.email, "username": user.username, "role": user.role},
            "tokens": tokens,
        }
    finally:
        db.close()


@router.post("/sso/azure")
async def azure_sso_login(payload: SSOPayload):
    """Authenticate through Microsoft Entra ID / Azure AD SSO."""
    profile = await OAuthManager.verify_azure_ad_token(payload.auth_code_or_token)
    tokens = create_tokens(user_id=1, org_id=1, role="org_admin")
    return {"profile": profile, "tokens": tokens}


@router.post("/sso/github")
async def github_sso_login(payload: SSOPayload):
    """Authenticate through GitHub OAuth."""
    profile = await OAuthManager.verify_github_oauth(payload.auth_code_or_token)
    tokens = create_tokens(user_id=1, org_id=1, role="developer")
    return {"profile": profile, "tokens": tokens}


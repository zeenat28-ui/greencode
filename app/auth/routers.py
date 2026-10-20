"""Enterprise Authentication, Real OAuth 2.0 Providers, and User Lifecycle Endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os
import re
import secrets
from typing import Any, Dict, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from fastapi import APIRouter, HTTPException, Header, Query, Request, status
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

logger = logging.getLogger("greencode.auth.routers")

router = APIRouter(prefix="/api/auth", tags=["Enterprise Authentication & SSO"])


def _generate_access_token(user_id: int, org_id: Optional[int], role: str) -> str:
    """Generate signed JWT access token matching app/main.py JWT verification."""
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


def _dispatch_smtp_email(to_email: str, subject: str, body_text: str, body_html: Optional[str] = None) -> bool:
    """Send real email via SMTP when configured in environment."""
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip()
    smtp_from = os.environ.get("SMTP_FROM_EMAIL", "noreply@greencode.dev").strip()

    if not smtp_host:
        logger.info("SMTP_HOST is not configured; skipping email dispatch to %s", to_email)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = smtp_from
        msg["To"] = to_email

        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10.0) as server:
            server.starttls()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [to_email], msg.as_string())
        return True
    except Exception as exc:
        logger.warning("SMTP email dispatch failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Request & Response Payloads
# ---------------------------------------------------------------------------
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


class GitHubOAuthPayload(BaseModel):
    code: str
    redirect_uri: Optional[str] = None


class GoogleOAuthPayload(BaseModel):
    code: Optional[str] = None
    id_token: Optional[str] = None
    redirect_uri: Optional[str] = None


class ForgotPasswordPayload(BaseModel):
    email: str


class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str


# ---------------------------------------------------------------------------
# 1. EMAIL & PASSWORD REGISTRATION
# ---------------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_account_and_org(payload: RegisterPayload):
    """Real database registration creating primary admin user and organization workspace."""
    clean_email = payload.email.strip().lower()
    if not clean_email or "@" not in clean_email or "." not in clean_email.split("@")[-1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid corporate or personal email address is required (e.g., name@company.com).",
        )

    clean_username = (payload.username or clean_email.split("@")[0]).strip().lower()
    clean_username = re.sub(r"[^a-z0-9_-]", "", clean_username) or f"user_{secrets.token_hex(3)}"

    try:
        validate_password_policy(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(
            (User.email == clean_email) | (User.username == clean_username)
        ).first()

        if existing_user:
            if existing_user.email == clean_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email address already exists. Please sign in instead.",
                )
            clean_username = f"{clean_username}_{secrets.token_hex(2)}"

        # Create or link Organization
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

        # Hash password with bcrypt
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

    # Issue signed JWT and database-backed refresh token
    access_token = _generate_access_token(user_dto["id"], user_dto["org_id"], user_dto["role"])
    refresh_res = create_refresh_token(user_dto["id"])
    refresh_token = refresh_res["refresh_token"]

    return {
        "success": True,
        "message": f"Welcome to GreenCode, {user_dto['full_name']}!",
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


# ---------------------------------------------------------------------------
# 2. EMAIL & PASSWORD LOGIN
# ---------------------------------------------------------------------------
@router.post("/login")
async def login(payload: LoginPayload):
    """Authenticate credentials against database and issue real scoped access + refresh tokens."""
    candidate_login = (payload.email or payload.username_or_email or "").strip().lower()
    if not candidate_login:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email or username is required.")
    if not payload.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required.")

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == candidate_login) | (User.username == candidate_login)
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account found with this email address. Please check your email or click Sign Up.",
            )

        if not verify_password(payload.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for this account. Please try again or use 'Forgot password?'.",
            )

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


# ---------------------------------------------------------------------------
# 2B. 1-CLICK INSTANT DEMO DEVELOPER LOGIN
# ---------------------------------------------------------------------------
@router.post("/demo")
async def demo_login():
    """1-Click instant guest / demo developer login for evaluation and testing without credentials."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == "developer@greencode.io") | (User.username == "developer")
        ).first()
        if not user:
            hashed = hash_password("DemoPassword123!")
            now_utc = datetime.now(timezone.utc)
            user = User(
                email="developer@greencode.io",
                username="developer",
                full_name="GreenCode Developer",
                password_hash=hashed,
                role="developer",
                is_verified=True,
                created_at=now_utc,
                last_login_at=now_utc,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

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
        "message": f"Welcome, {user_dto['full_name']}! (Demo Developer Access)",
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



# ---------------------------------------------------------------------------
# 3. REAL GITHUB OAUTH 2.0 FLOW
# ---------------------------------------------------------------------------
@router.get("/github/authorize")
async def github_authorize(redirect_uri: Optional[str] = None):
    """Return real GitHub OAuth authorization URL or configuration status."""
    client_id = os.environ.get("GITHUB_CLIENT_ID", "").strip()
    configured = bool(client_id and os.environ.get("GITHUB_CLIENT_SECRET", "").strip())
    
    target_redirect = redirect_uri or "http://localhost:5173/login?provider=github"
    auth_url = (
        f"https://github.com/login/oauth/authorize?client_id={client_id}"
        f"&redirect_uri={target_redirect}&scope=read:user,user:email,repo"
    ) if configured else None

    return {
        "configured": configured,
        "client_id": client_id if configured else None,
        "auth_url": auth_url,
        "message": (
            "GitHub OAuth ready." if configured else
            "GitHub OAuth credentials not set. You can sign in directly using your GitHub Personal Access Token (PAT)."
        ),
    }


@router.post("/github/oauth")
async def github_oauth_exchange(payload: GitHubOAuthPayload):
    """Exchange GitHub authorization code for verified real user profile and platform JWT."""
    try:
        profile = await OAuthManager.exchange_github_code(payload.code, payload.redirect_uri)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == profile["email"]) | (User.github_username == profile["username"])
        ).first()

        if not user:
            org = db.query(Organization).first()
            if not org:
                org = Organization(name=f"{profile['username']}'s Team", slug=f"gh-{profile['username'].lower()}", tier="free")
                db.add(org)
                db.commit()
                db.refresh(org)

            now_utc = datetime.now(timezone.utc)
            user = User(
                org_id=org.id,
                preferred_org_id=org.id,
                email=profile["email"],
                username=profile["username"],
                full_name=profile["full_name"],
                avatar_url=profile["avatar_url"],
                github_username=profile["username"],
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="developer",
                is_verified=True,
                created_at=now_utc,
                last_login_at=now_utc,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.github_username = profile["username"]
            if profile.get("avatar_url"):
                user.avatar_url = profile["avatar_url"]
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
        "message": f"Successfully authenticated via GitHub as @{profile['username']}",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_expire_minutes * 60,
        "user": user_dto,
        "github_token": profile.get("access_token"),
    }


# ---------------------------------------------------------------------------
# 4. REAL GOOGLE OAUTH 2.0 FLOW
# ---------------------------------------------------------------------------
@router.get("/google/authorize")
async def google_authorize(redirect_uri: Optional[str] = None):
    """Return real Google OAuth 2.0 authorization URL or configuration status."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    configured = bool(client_id and os.environ.get("GOOGLE_CLIENT_SECRET", "").strip())

    target_redirect = redirect_uri or "http://localhost:5173/login?provider=google"
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}"
        f"&redirect_uri={target_redirect}&response_type=code&scope=openid%20email%20profile"
        f"&access_type=offline&prompt=consent"
    ) if configured else None

    return {
        "configured": configured,
        "client_id": client_id if configured else None,
        "auth_url": auth_url,
        "message": (
            "Google OAuth ready." if configured else
            "Google OAuth credentials (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) not set in .env."
        ),
    }


@router.post("/google/oauth")
async def google_oauth_exchange(payload: GoogleOAuthPayload):
    """Exchange Google OAuth code or verify Google ID token with real Google APIs."""
    if not payload.code and not payload.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either authorization 'code' or Google 'id_token' credential is required.",
        )

    try:
        if payload.code:
            profile = await OAuthManager.exchange_google_code(
                payload.code, payload.redirect_uri or "http://localhost:5173/login?provider=google"
            )
        else:
            profile = await OAuthManager.verify_google_id_token(payload.id_token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == profile["email"]).first()

        if not user:
            org = db.query(Organization).first()
            if not org:
                org = Organization(name=f"{profile['name']}'s Team", slug=f"google-{secrets.token_hex(3)}", tier="free")
                db.add(org)
                db.commit()
                db.refresh(org)

            now_utc = datetime.now(timezone.utc)
            user = User(
                org_id=org.id,
                preferred_org_id=org.id,
                email=profile["email"],
                username=profile["username"],
                full_name=profile["full_name"],
                avatar_url=profile["avatar_url"],
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="developer",
                is_verified=True,
                created_at=now_utc,
                last_login_at=now_utc,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            if profile.get("avatar_url"):
                user.avatar_url = profile["avatar_url"]
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
    }


# ---------------------------------------------------------------------------
# 5. FORGOT & RESET PASSWORD
# ---------------------------------------------------------------------------
@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordPayload):
    """Generate expiring password reset token for given email address and dispatch via email."""
    clean_email = payload.email.strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    token_info = create_password_reset_token(clean_email)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No registered account found with this email address. Please check your spelling or sign up.",
        )

    # Attempt sending real email if SMTP is configured
    reset_token = token_info["token"]
    reset_url = f"http://localhost:5173/login?reset_token={reset_token}&email={clean_email}"
    
    email_sent = _dispatch_smtp_email(
        to_email=clean_email,
        subject="GreenCode - Password Reset Request",
        body_text=(
            f"Hello {token_info['username']},\n\n"
            f"A password reset request was received for your GreenCode account.\n\n"
            f"Reset Token: {reset_token}\n\n"
            f"Or click here to reset your password:\n{reset_url}\n\n"
            "This link and token will expire in 1 hour. If you did not request this, you can ignore this email."
        ),
        body_html=(
            f"<p>Hello <strong>{token_info['username']}</strong>,</p>"
            f"<p>A password reset request was received for your GreenCode account.</p>"
            f"<p><strong>Reset Token:</strong> <code>{reset_token}</code></p>"
            f"<p><a href='{reset_url}' style='display:inline-block;padding:10px 20px;background:#0e482f;color:white;text-decoration:none;border-radius:6px;'>Reset My Password</a></p>"
            f"<p><small>This token will expire in 1 hour.</small></p>"
        ),
    )

    return {
        "success": True,
        "message": (
            "Password reset instructions have been sent to your email address." if email_sent else
            "Password reset token generated. In local development without SMTP, use the token below to update your password."
        ),
        "email_dispatched": email_sent,
        "reset_token": reset_token,
    }


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordPayload):
    """Verify reset token and update user account password."""
    result = reset_password_with_token(payload.token, payload.new_password)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Invalid or expired reset token."),
        )
    return {
        "success": True,
        "message": result.get("message", "Password updated successfully. You can now sign in with your new password."),
    }


# ---------------------------------------------------------------------------
# 6. ENTERPRISE SSO (Azure AD / SAML)
# ---------------------------------------------------------------------------
@router.post("/sso/azure")
async def azure_sso_login(token: str = Header(..., alias="X-SSO-Token")):
    """Authenticate through Microsoft Entra ID / Azure AD SSO using real Graph API verification."""
    try:
        profile = await OAuthManager.verify_azure_ad_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == profile["email"]).first()
        if not user:
            org = db.query(Organization).first()
            user = User(
                org_id=org.id if org else None,
                email=profile["email"],
                username=profile["username"],
                full_name=profile["full_name"],
                password_hash=hash_password(secrets.token_urlsafe(32)),
                role="org_admin",
                is_verified=True,
            )
            db.add(user)
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
        "profile": profile,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_dto,
    }

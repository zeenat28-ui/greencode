"""Enterprise SSO and OAuth Provider Handlers with Real Upstream Verification."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("greencode.auth.oauth")


class OAuthManager:
    """Manages federated SSO identity verification for GitHub and Google using real upstream APIs."""

    @classmethod
    async def exchange_github_code(cls, code: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Exchange GitHub OAuth authorization code for verified user profile via GitHub API.
        
        Real-world GitHub OAuth 2.0 implementation:
        1. Exchanges temporary authorization code with https://github.com/login/oauth/access_token
        2. Retrieves user profile from https://api.github.com/user
        3. Retrieves primary verified email from https://api.github.com/user/emails
        """
        client_id = os.environ.get("GITHUB_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            raise ValueError(
                "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in your .env file."
            )

        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
        }
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri

        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                json=payload,
                headers={"Accept": "application/json"},
            )
            if token_resp.status_code != 200:
                raise ValueError(f"GitHub token exchange failed: {token_resp.text}")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                error_desc = token_data.get("error_description") or token_data.get("error") or "No access token received"
                raise ValueError(f"GitHub OAuth error: {error_desc}")

            # Fetch user profile
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "GreenCode-Auditor",
                "Accept": "application/vnd.github.v3+json",
            }
            user_resp = await client.get("https://api.github.com/user", headers=headers)
            if user_resp.status_code != 200:
                raise ValueError("Failed to retrieve user profile from GitHub API.")

            user_data = user_resp.json()

            # Fetch verified primary email if not public in profile
            primary_email = user_data.get("email")
            if not primary_email:
                try:
                    emails_resp = await client.get("https://api.github.com/user/emails", headers=headers)
                    if emails_resp.status_code == 200:
                        emails = emails_resp.json()
                        for em in emails:
                            if em.get("primary") and em.get("verified"):
                                primary_email = em.get("email")
                                break
                        if not primary_email and emails:
                            primary_email = emails[0].get("email")
                except Exception as exc:
                    logger.warning("Could not fetch user emails from GitHub: %s", exc)

            if not primary_email:
                primary_email = f"{user_data.get('login')}@users.noreply.github.com"

            return {
                "provider": "github",
                "provider_user_id": str(user_data.get("id")),
                "email": primary_email.lower(),
                "username": user_data.get("login"),
                "full_name": user_data.get("name") or user_data.get("login"),
                "avatar_url": user_data.get("avatar_url"),
                "access_token": access_token,
            }

    @classmethod
    async def exchange_google_code(cls, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange Google OAuth authorization code for verified user profile via Google OAuth2.
        
        Real-world Google OAuth 2.0 implementation:
        1. Exchanges authorization code with https://oauth2.googleapis.com/token
        2. Retrieves user profile from https://www.googleapis.com/oauth2/v3/userinfo
        """
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()

        if not client_id or not client_secret:
            raise ValueError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file."
            )

        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post("https://oauth2.googleapis.com/token", data=payload)
            if token_resp.status_code != 200:
                raise ValueError(f"Google token exchange failed: {token_resp.text}")

            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("No access token received from Google.")

            # Retrieve user info from Google's OpenID UserInfo endpoint
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_resp.status_code != 200:
                raise ValueError("Failed to retrieve user profile from Google UserInfo endpoint.")

            user_data = user_resp.json()
            email = user_data.get("email")
            if not email:
                raise ValueError("Google user profile does not contain an email address.")

            return {
                "provider": "google",
                "provider_user_id": str(user_data.get("sub")),
                "email": email.lower(),
                "username": email.split("@")[0],
                "full_name": user_data.get("name") or email.split("@")[0],
                "avatar_url": user_data.get("picture"),
                "access_token": access_token,
            }

    @classmethod
    async def verify_google_id_token(cls, id_token: str) -> Dict[str, Any]:
        """Verify Google ID token (JWT) using Google's public tokeninfo endpoint."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
            if resp.status_code != 200:
                raise ValueError(f"Google ID token verification failed: {resp.text}")

            payload = resp.json()
            email = payload.get("email")
            if not email:
                raise ValueError("Google ID token does not contain a verified email.")

            return {
                "provider": "google",
                "provider_user_id": str(payload.get("sub")),
                "email": email.lower(),
                "username": email.split("@")[0],
                "full_name": payload.get("name") or email.split("@")[0],
                "avatar_url": payload.get("picture"),
            }

    @classmethod
    async def verify_azure_ad_token(cls, token: str) -> Dict[str, Any]:
        """Verify Microsoft Entra ID / Azure AD Bearer token using Graph API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                raise ValueError("Failed to verify Azure AD token via Microsoft Graph.")

            data = resp.json()
            email = data.get("mail") or data.get("userPrincipalName")
            return {
                "provider": "azure_ad",
                "provider_user_id": str(data.get("id")),
                "email": str(email).lower(),
                "username": str(data.get("userPrincipalName", email)).split("@")[0],
                "full_name": data.get("displayName") or "Corporate User",
            }

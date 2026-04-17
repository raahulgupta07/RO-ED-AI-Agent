#!/usr/bin/env python3
"""Auth routes for RO-ED AI Agent — dual-mode (local + Keycloak OIDC)"""

import json
import logging
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import URLError

from fastapi import APIRouter, Depends, HTTPException, status

import auth
import config
import database
from middleware import get_current_user
from schemas import (
    LoginRequest, TokenResponse, UserResponse,
    OIDCConfigResponse, TokenExchangeRequest, TokenExchangeResponse,
    RefreshTokenRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# AUTH CONFIG — tells frontend which mode to use
# =============================================================================

@router.get("/config", response_model=OIDCConfigResponse)
async def get_auth_config():
    """Public endpoint: returns auth mode and OIDC endpoints if Keycloak enabled."""
    kc = config.get_keycloak_config()
    if kc:
        return OIDCConfigResponse(
            mode="keycloak",
            auth_url=kc["auth_url"],
            token_url=kc["token_url"],
            logout_url=kc["logout_url"],
            client_id=kc["client_id"],
        )
    return OIDCConfigResponse(mode="local")


# =============================================================================
# LOCAL LOGIN (used when Keycloak is disabled)
# =============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user with username/password (works in both modes)."""
    user = database.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token_data = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }
    access_token = auth.create_access_token(token_data)

    database.log_activity(user["id"], user["username"], "LOGIN", "Session started")

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"],
            username=user["username"],
            display_name=user.get("display_name", ""),
            role=user["role"],
            is_active=True,
        ),
    )


# =============================================================================
# KEYCLOAK OIDC TOKEN EXCHANGE
# =============================================================================

@router.post("/token", response_model=TokenExchangeResponse)
async def exchange_token(request: TokenExchangeRequest):
    """Exchange OIDC authorization code for tokens via Keycloak."""
    kc = config.get_keycloak_config()
    if not kc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keycloak not configured",
        )

    # Build token request to Keycloak
    data = {
        "grant_type": "authorization_code",
        "code": request.code,
        "redirect_uri": request.redirect_uri,
        "client_id": kc["client_id"],
        "code_verifier": request.code_verifier,
    }
    if kc.get("client_secret"):
        data["client_secret"] = kc["client_secret"]

    try:
        body = urlencode(data).encode()
        req = Request(
            kc["token_url"],
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode())
    except URLError as e:
        logger.error(f"Keycloak token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Keycloak token exchange failed: {e}",
        )

    if "error" in token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=token_data.get("error_description", token_data["error"]),
        )

    # Auto-provision user from the access token
    try:
        payload = auth.verify_keycloak_token(token_data["access_token"])
        user_info = auth.extract_user_info(payload)
        user = database.upsert_keycloak_user(
            keycloak_id=user_info["sub"],
            username=user_info["username"],
            display_name=user_info["display_name"],
            email=user_info["email"],
            role=user_info["role"],
        )
        database.log_activity(user["id"], user["username"], "LOGIN", "Keycloak SSO")
    except Exception as e:
        logger.warning(f"User provisioning after token exchange: {e}")

    return TokenExchangeResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 300),
    )


# =============================================================================
# KEYCLOAK TOKEN REFRESH
# =============================================================================

@router.post("/refresh", response_model=TokenExchangeResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh Keycloak access token using refresh token."""
    kc = config.get_keycloak_config()
    if not kc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Keycloak not configured",
        )

    data = {
        "grant_type": "refresh_token",
        "refresh_token": request.refresh_token,
        "client_id": kc["client_id"],
    }
    if kc.get("client_secret"):
        data["client_secret"] = kc["client_secret"]

    try:
        body = urlencode(data).encode()
        req = Request(
            kc["token_url"],
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urlopen(req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode())
    except URLError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token refresh failed: {e}",
        )

    if "error" in token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=token_data.get("error_description", token_data["error"]),
        )

    return TokenExchangeResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        expires_in=token_data.get("expires_in", 300),
    )


# =============================================================================
# CURRENT USER + LOGOUT
# =============================================================================

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info with permissions."""
    permissions = database.get_user_permissions(current_user)
    group = database.get_user_group(current_user["id"])

    # Determine auth type
    all_users = database.get_all_users()
    user_row = next((u for u in all_users if u["id"] == current_user["id"]), None)
    has_keycloak = bool(user_row and user_row.get("keycloak_id")) if user_row else False

    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "display_name": current_user.get("display_name", ""),
        "role": current_user["role"],
        "email": user_row.get("email", "") if user_row else "",
        "auth_type": "keycloak" if has_keycloak else "local",
        "group": {"id": group["id"], "name": group["name"]} if group else None,
        "permissions": permissions,
    }


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Log the logout event. Client should discard the token."""
    database.log_activity(
        current_user["id"], current_user["username"], "LOGOUT", "Session ended"
    )
    return {"message": "Logged out"}

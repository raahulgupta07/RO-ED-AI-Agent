#!/usr/bin/env python3
"""Settings routes for RO-ED AI Agent — Keycloak configuration (admin only)"""

from fastapi import APIRouter, Depends

import auth
import config
import database
from middleware import require_admin
from schemas import KeycloakSettingsRequest, KeycloakSettingsResponse, KeycloakTestResponse

router = APIRouter()


@router.get("/keycloak", response_model=KeycloakSettingsResponse)
async def get_keycloak_settings(admin: dict = Depends(require_admin)):
    """Get current Keycloak settings (admin only)."""
    settings = database.get_settings_by_prefix("keycloak_")

    return KeycloakSettingsResponse(
        realm_url=settings.get("keycloak_realm_url", {}).get("value", ""),
        client_id=settings.get("keycloak_client_id", {}).get("value", ""),
        client_secret=settings.get("keycloak_client_secret", {}).get("value", ""),
        admin_role=settings.get("keycloak_admin_role", {}).get("value", "admin"),
        enabled=settings.get("keycloak_enabled", {}).get("value", "false") == "true",
        updated_at=settings.get("keycloak_realm_url", {}).get("updated_at"),
    )


@router.put("/keycloak", response_model=KeycloakSettingsResponse)
async def save_keycloak_settings(
    request: KeycloakSettingsRequest,
    admin: dict = Depends(require_admin),
):
    """Save Keycloak settings (admin only). Invalidates cache immediately."""
    username = admin["username"]

    database.set_setting("keycloak_realm_url", request.realm_url.rstrip("/"), username)
    database.set_setting("keycloak_client_id", request.client_id, username)
    database.set_setting("keycloak_client_secret", request.client_secret, username)
    database.set_setting("keycloak_admin_role", request.admin_role or "admin", username)
    database.set_setting("keycloak_enabled", "true" if request.enabled else "false", username)

    # Invalidate cache so changes take effect immediately
    config.invalidate_keycloak_cache()

    database.log_activity(
        admin["id"], username, "UPDATE_SETTINGS",
        f"Keycloak {'enabled' if request.enabled else 'disabled'} — realm: {request.realm_url}",
    )

    return KeycloakSettingsResponse(
        realm_url=request.realm_url,
        client_id=request.client_id,
        client_secret=request.client_secret,
        admin_role=request.admin_role,
        enabled=request.enabled,
    )


@router.post("/keycloak/test", response_model=KeycloakTestResponse)
async def test_keycloak_connection(
    request: KeycloakSettingsRequest,
    admin: dict = Depends(require_admin),
):
    """Test Keycloak connection by fetching JWKS from realm URL (admin only)."""
    if not request.realm_url:
        return KeycloakTestResponse(success=False, message="Realm URL is required", keys_found=0)

    result = auth.test_keycloak_connection(request.realm_url.rstrip("/"))
    return KeycloakTestResponse(**result)

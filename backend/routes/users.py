#!/usr/bin/env python3
"""User management routes for RO-ED AI Agent (admin only)"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

import config
import database
from middleware import require_admin, get_current_user
from schemas import (
    CreateUserRequest, UpdateUserRequest, UserListResponse,
    ActivityLogResponse,
)

router = APIRouter()


@router.get("/")
async def list_users(admin: dict = Depends(require_admin)):
    """List all users with group info (admin only)."""
    users = database.get_all_users_with_groups()
    return users


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(request: CreateUserRequest, admin: dict = Depends(require_admin)):
    """Create a new user (admin only). Blocked when Keycloak is enabled."""
    if config.get_keycloak_config():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User management is handled in Keycloak",
        )
    success = database.create_user(
        request.username, request.password, request.display_name, request.role
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request.username}' already exists",
        )
    database.log_activity(
        admin["id"], admin["username"], "CREATE_USER",
        f"Created user: {request.username} ({request.role})"
    )
    return {"message": f"User '{request.username}' created"}


@router.put("/{user_id}")
async def update_user(user_id: int, request: UpdateUserRequest, admin: dict = Depends(require_admin)):
    """Update a user (admin only). Blocked when Keycloak is enabled."""
    if config.get_keycloak_config():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User management is handled in Keycloak",
        )
    database.update_user(
        user_id,
        display_name=request.display_name,
        role=request.role,
        is_active=request.is_active if request.is_active is not None else None,
        password=request.password,
    )
    database.log_activity(
        admin["id"], admin["username"], "UPDATE_USER",
        f"Updated user ID {user_id}"
    )
    return {"message": "User updated"}


@router.delete("/{user_id}")
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    """Delete a user (admin only). Blocked when Keycloak is enabled."""
    if config.get_keycloak_config():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User management is handled in Keycloak",
        )
    if user_id == admin["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    success = database.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    database.log_activity(
        admin["id"], admin["username"], "DELETE_USER",
        f"Deleted user ID {user_id}"
    )
    return {"message": "User deleted"}


@router.get("/activity-logs", response_model=List[ActivityLogResponse])
async def get_activity_logs(
    limit: int = 200,
    user_id: int = None,
    admin: dict = Depends(require_admin),
):
    """Get activity logs (admin only)."""
    logs = database.get_activity_logs(limit=limit, user_id=user_id)
    return [ActivityLogResponse(**log) for log in logs]

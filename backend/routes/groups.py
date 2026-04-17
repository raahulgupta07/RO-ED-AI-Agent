#!/usr/bin/env python3
"""Group management routes for RO-ED AI Agent (admin only)"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

import database
from middleware import require_admin
from schemas import GroupRequest, GroupResponse, AssignGroupRequest

router = APIRouter()


@router.get("/", response_model=List[GroupResponse])
async def list_groups(admin: dict = Depends(require_admin)):
    """List all groups with member count."""
    groups = database.get_all_groups()
    return [GroupResponse(**g) for g in groups]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_group(request: GroupRequest, admin: dict = Depends(require_admin)):
    """Create a new group."""
    kwargs = request.model_dump(exclude={"name", "description", "member_ids"})
    gid = database.create_group(request.name, request.description, **kwargs)
    if gid is None:
        raise HTTPException(status_code=409, detail=f"Group '{request.name}' already exists")

    if request.member_ids:
        database.set_group_members(gid, request.member_ids, admin["username"])

    database.log_activity(admin["id"], admin["username"], "CREATE_GROUP", f"Created group: {request.name}")
    return {"id": gid, "message": f"Group '{request.name}' created"}


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(group_id: int, admin: dict = Depends(require_admin)):
    """Get a single group with members."""
    group = database.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    group["members"] = database.get_group_members(group_id)
    group["member_count"] = len(group["members"])
    return GroupResponse(**group)


@router.put("/{group_id}")
async def update_group(group_id: int, request: GroupRequest, admin: dict = Depends(require_admin)):
    """Update a group's permissions and members."""
    group = database.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    kwargs = request.model_dump(exclude={"member_ids"})
    database.update_group(group_id, **kwargs)

    database.set_group_members(group_id, request.member_ids, admin["username"])

    database.log_activity(admin["id"], admin["username"], "UPDATE_GROUP", f"Updated group: {request.name}")
    return {"message": f"Group '{request.name}' updated"}


@router.delete("/{group_id}")
async def delete_group(group_id: int, admin: dict = Depends(require_admin)):
    """Delete a group."""
    group = database.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    database.delete_group(group_id)
    database.log_activity(admin["id"], admin["username"], "DELETE_GROUP", f"Deleted group: {group['name']}")
    return {"message": f"Group '{group['name']}' deleted"}


@router.put("/assign/{user_id}")
async def assign_user_group(user_id: int, request: AssignGroupRequest, admin: dict = Depends(require_admin)):
    """Assign a user to a group (or remove from all groups)."""
    database.set_user_group(user_id, request.group_id, admin["username"])
    database.log_activity(
        admin["id"], admin["username"], "ASSIGN_GROUP",
        f"User {user_id} → group {request.group_id or 'none'}",
    )
    return {"message": "Group assignment updated"}

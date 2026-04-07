"""
Favorites API.

Provides endpoints for managing favorite records.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.user_assets.favorites import (
    FavoriteCreateRequest,
    FavoriteDeleteResponse,
    FavoriteListResponse,
    FavoriteResponse,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.user_assets import favorites as fav_svc

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("", response_model=dict)
async def add_favorite(
    current_user: AuthUserDep,
    body: FavoriteCreateRequest,
) -> dict:
    """Add a favorite (upsert by target_type + target_key)."""
    try:
        fav_id = await fav_svc.add_favorite(
            user_id=UUID(current_user.user_id),
            target_type=body.target_type,
            target_key=body.target_key,
            analysis_record_id=body.analysis_record_id,
            payload_json=body.payload_json,
            note=body.note,
        )
        return {"id": str(fav_id), "ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=FavoriteListResponse)
async def list_favorites(
    current_user: AuthUserDep,
) -> FavoriteListResponse:
    """List all favorites for the current user."""
    try:
        items = await fav_svc.list_favorites(
            user_id=UUID(current_user.user_id),
        )
        return FavoriteListResponse(
            items=[FavoriteResponse(**row) for row in items],
            total=len(items),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{analysis_record_id}", response_model=FavoriteDeleteResponse)
async def remove_favorite(
    current_user: AuthUserDep,
    analysis_record_id: UUID,
) -> FavoriteDeleteResponse:
    """Remove a favorite by analysis_record_id."""
    try:
        count = await fav_svc.remove_favorite_by_analysis_record(
            user_id=UUID(current_user.user_id),
            analysis_record_id=analysis_record_id,
        )
        return FavoriteDeleteResponse(deleted=count > 0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

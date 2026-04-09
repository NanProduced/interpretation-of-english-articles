"""
User Quota API.

Provides endpoints for checking user credit/quota information.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.analysis.credit_service import ensure_credit_account, get_quota_info
from app.services.auth.dependencies import AuthUserDep

router = APIRouter(prefix="/me", tags=["user"])


class QuotaResponse(BaseModel):
    """GET /me/quota response."""

    daily_free_points: int
    daily_used_points: int
    bonus_points: int
    remaining_points: int


@router.get("/quota", response_model=QuotaResponse)
async def get_user_quota(
    current_user: AuthUserDep,
) -> QuotaResponse:
    """
    Get current user's quota information.

    Returns daily free points, used points, bonus points, and remaining total.
    Performs lazy daily reset if needed.
    """
    try:
        user_id = UUID(current_user.user_id)
        await ensure_credit_account(user_id)
        info = await get_quota_info(user_id)
        return QuotaResponse(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

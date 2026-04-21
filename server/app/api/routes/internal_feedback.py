"""
Internal Feedback Management API.

Provides endpoints for cloud backend to manage feedback status and rewards.
Uses API Key authentication instead of user session.
"""

from __future__ import annotations

import secrets
from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from app.config.settings import get_settings
from app.schemas.feedback import (
    FeedbackRewardRequest,
    FeedbackStatusUpdateRequest,
)
from app.services.analysis.credit_service import grant_bonus_credits
from app.services.feedback import service as feedback_svc

logger = getLogger("app.api")

router = APIRouter(prefix="/internal/feedback", tags=["internal"])


class FeedbackRewardResponse(BaseModel):
    feedback_id: str
    user_id: str
    reward_points: int
    granted: bool


def _verify_internal_key(x_internal_key: str | None) -> None:
    settings = get_settings()
    if not settings.internal_api_key:
        raise HTTPException(status_code=503, detail="Internal API not configured")
    if x_internal_key is None or not secrets.compare_digest(x_internal_key, settings.internal_api_key):
        raise HTTPException(status_code=403, detail="Invalid internal API key")


@router.patch("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: UUID,
    body: FeedbackStatusUpdateRequest,
    x_internal_key: str | None = Header(default=None),
) -> dict:
    _verify_internal_key(x_internal_key)
    row = await feedback_svc.update_feedback_status(
        feedback_id=feedback_id,
        status=body.status,
        admin_note=body.admin_note,
        reviewed_by=None,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return row


@router.post("/{feedback_id}/reward", response_model=FeedbackRewardResponse)
async def reward_feedback(
    feedback_id: UUID,
    body: FeedbackRewardRequest,
    x_internal_key: str | None = Header(default=None),
) -> dict:
    _verify_internal_key(x_internal_key)
    row = await feedback_svc.reward_feedback(
        feedback_id=feedback_id,
        points=body.points,
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Feedback not found or already adopted",
        )

    user_id = row["user_id"]
    granted = await grant_bonus_credits(
        user_id=user_id,
        points=body.points,
        entry_type="feedback_reward",
        metadata={"feedback_id": str(feedback_id)},
    )
    return {
        "feedback_id": str(feedback_id),
        "user_id": str(user_id),
        "reward_points": body.points,
        "granted": granted,
    }


@router.get("/stats")
async def get_feedback_stats(
    x_internal_key: str | None = Header(default=None),
) -> dict:
    _verify_internal_key(x_internal_key)
    return await feedback_svc.get_feedback_stats()

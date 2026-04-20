"""
Feedback API.

Provides endpoints for submitting and managing user feedback.
"""

from __future__ import annotations

from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from app.schemas.feedback import (
    FeedbackCreateRequest,
    FeedbackListResponse,
    FeedbackListItem,
    FeedbackResponse,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.feedback import service as feedback_svc

logger = getLogger("app.api")

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(
    current_user: AuthUserDep,
    body: FeedbackCreateRequest,
) -> FeedbackResponse:
    user_id = UUID(current_user.user_id)
    row = await feedback_svc.submit_feedback(
        user_id=user_id,
        feedback_scope=body.feedback_scope,
        target_id=body.target_id,
        analysis_record_id=body.analysis_record_id,
        sentiment=body.sentiment,
        feedback_type=body.feedback_type,
        annotation_type=body.annotation_type,
        content=body.content,
        context_json=body.context_json,
        app_version=body.app_version,
    )
    return FeedbackResponse(
        id=row["id"],
        feedback_scope=row["feedback_scope"],
        target_id=row["target_id"],
        sentiment=row["sentiment"],
        feedback_type=row["feedback_type"],
        status=row["status"],
        created_at=row["created_at"],
    )


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    current_user: AuthUserDep,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    feedback_scope: str | None = Query(default=None),
) -> FeedbackListResponse:
    user_id = UUID(current_user.user_id)
    items, next_cursor, has_more = await feedback_svc.list_user_feedback(
        user_id=user_id,
        cursor=cursor,
        limit=limit,
        feedback_scope=feedback_scope,
    )
    return FeedbackListResponse(
        items=[
            FeedbackListItem(
                id=item["id"],
                feedback_scope=item["feedback_scope"],
                feedback_type=item["feedback_type"],
                sentiment=item["sentiment"],
                content=item.get("content"),
                status=item["status"],
                reward_points=item.get("reward_points", 0),
                created_at=item["created_at"],
            )
            for item in items
        ],
        cursor=next_cursor,
        has_more=has_more,
    )


@router.delete("/{feedback_id}", status_code=204)
async def delete_feedback(
    current_user: AuthUserDep,
    feedback_id: UUID,
) -> Response:
    user_id = UUID(current_user.user_id)
    deleted = await feedback_svc.delete_feedback(user_id=user_id, feedback_id=feedback_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Feedback not found or not deletable (only pending feedback can be deleted)",
        )
    return Response(status_code=204)

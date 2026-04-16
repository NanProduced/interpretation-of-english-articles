"""
Feedback API.

Provides endpoints for submitting and managing user feedback.
用于收集用户反馈，为后续 RAG 的 few-shot 注入做准备。
"""

from __future__ import annotations

from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.user_assets.feedbacks import (
    CreateFeedbackRequest,
    FeedbackCreateResponse,
    FeedbackListResponse,
    FeedbackResponse,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.user_assets import feedbacks as feedbacks_svc

logger = getLogger("app.api")

router = APIRouter(prefix="/feedbacks", tags=["feedbacks"])


@router.post("", response_model=FeedbackCreateResponse)
async def submit_feedback(
    current_user: AuthUserDep,
    body: CreateFeedbackRequest,
) -> FeedbackCreateResponse:
    """
    提交用户反馈。

    支持以下反馈类型：
    - result_overall: 结果页整体反馈
    - grammar_note: 语法标注反馈
    - sentence_analysis: 句式分析反馈
    - vocab_entry: 词汇卡片反馈
    - general: 通用反馈（从个人中心提交）

    所有反馈类型都支持：
    - satisfaction: 是否满意（可选）
    - category: 反馈分类（不满意时选择）
    - detail_text: 用户输入的详细理由
    - context_json: 上下文数据（根据不同反馈类型存储不同信息）
    """
    try:
        feedback_id = await feedbacks_svc.create_feedback(
            user_id=UUID(current_user.user_id),
            feedback_type=body.feedback_type.value,
            satisfaction=body.satisfaction,
            category=body.category.value if body.category else None,
            detail_text=body.detail_text,
            analysis_record_id=body.analysis_record_id,
            context_json=body.context_json,
            client_metadata_json=body.client_metadata_json,
        )

        return FeedbackCreateResponse(
            id=feedback_id,
            created=True,
            created_at=feedback_id,  # This will be replaced with actual timestamp
        )
    except Exception as e:
        logger.error("submit_feedback failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=FeedbackListResponse)
async def list_feedbacks(
    current_user: AuthUserDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    feedback_type: str | None = Query(default=None),
    satisfaction: bool | None = Query(default=None),
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> FeedbackListResponse:
    """
    获取当前用户的反馈列表（分页）。

    可通过以下参数筛选：
    - feedback_type: 反馈类型
    - satisfaction: 是否满意
    - category: 反馈分类
    - status: 处理状态
    """
    try:
        items, total = await feedbacks_svc.list_feedbacks(
            user_id=UUID(current_user.user_id),
            page=page,
            limit=limit,
            feedback_type=feedback_type,
            satisfaction=satisfaction,
            category=category,
            status=status,
        )
        return FeedbackListResponse(
            items=[FeedbackResponse(**row) for row in items],
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error("list_feedbacks failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    current_user: AuthUserDep,
    feedback_id: UUID,
) -> FeedbackResponse:
    """
    获取单条反馈详情。
    """
    try:
        feedback = await feedbacks_svc.get_feedback_by_id(
            feedback_id=feedback_id,
            user_id=UUID(current_user.user_id),
        )
        if feedback is None:
            raise HTTPException(status_code=404, detail="Feedback not found")
        return FeedbackResponse(**feedback)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_feedback failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/check/should-trigger", response_model=dict)
async def check_should_trigger(
    current_user: AuthUserDep,
    source_text_length: int = Query(ge=0),
    processing_ms: int | None = Query(default=None),
    user_facing_state: str | None = Query(default=None),
) -> dict:
    """
    检查是否应该弹出结果页反馈询问。

    前端可调用此接口来决定是否显示反馈弹窗。

    触发规则：
    1. 文本字符数 > 300
    2. 响应时间 > 60 秒
    3. 结果状态为降级状态

    同时限制：24 小时内最多弹出 3 次
    """
    try:
        should_trigger = await feedbacks_svc.should_trigger_feedback_popup(
            user_id=UUID(current_user.user_id),
            source_text_length=source_text_length,
            processing_ms=processing_ms,
            user_facing_state=user_facing_state,
        )
        return {"should_trigger": should_trigger}
    except Exception as e:
        logger.error("check_should_trigger failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

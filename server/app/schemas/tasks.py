"""
Analysis Tasks API Schemas.

Defines request/response Pydantic models for /analysis-tasks endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.analysis import AnyRenderSceneModel
from app.schemas.analysis import GOAL_VARIANT_MAP
from app.schemas.internal.analysis import ReadingGoal, ReadingVariant

# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

TaskStatus = Literal[
    "queued", "running", "finalizing", "succeeded", "failed", "cancelled", "expired"
]


class TaskSubmitRequest(BaseModel):
    """POST /analysis-tasks — submit a new analysis task."""

    text: str = Field(min_length=1, description="待分析的原始英文文本。")
    reading_goal: ReadingGoal = Field(default="daily_reading")
    reading_variant: ReadingVariant = Field(default="intermediate_reading")
    source_type: Literal["user_input", "daily_article", "ocr"] = Field(default="user_input")
    extended: bool = Field(default=False)
    wait_for_result: bool = Field(
        default=False,
        description="是否在本次请求内等待任务结果（超时后仍返回任务状态）。",
    )
    wait_timeout_seconds: float = Field(
        default=45.0,
        ge=1.0,
        le=120.0,
        description="当 wait_for_result=true 时，最长等待秒数。",
    )

    def model_post_init(self, __context__: Any) -> None:
        allowed_variants = GOAL_VARIANT_MAP[self.reading_goal]
        if self.reading_variant not in allowed_variants:
            raise ValueError(
                f"reading_variant={self.reading_variant} does not match "
                f"reading_goal={self.reading_goal}"
            )


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class TaskSubmitResponse(BaseModel):
    """202 response after task submission."""

    task_id: UUID
    record_id: UUID
    status: TaskStatus
    created: bool = Field(description="当前实现恒为 True，保留该字段用于响应兼容。")
    render_scene: AnyRenderSceneModel | None = Field(
        default=None,
        description="当 wait_for_result=true 且任务在超时前成功完成时返回。",
    )


class TaskStatusResponse(BaseModel):
    """GET /analysis-tasks/{id} response."""

    task_id: UUID
    record_id: UUID
    status: TaskStatus
    failure_code: str | None = None
    failure_message: str | None = None
    quota_cost_points: int = 0
    queued_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ActiveTaskResponse(BaseModel):
    """GET /analysis-tasks/current — returns current active task or null indicator."""

    has_active: bool
    task: TaskStatusResponse | None = None

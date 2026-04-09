"""
Analysis Tasks API Schemas.

Defines request/response Pydantic models for /analysis-tasks endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

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
    idempotency_key: str = Field(
        min_length=1,
        max_length=64,
        description="客户端生成的幂等键，同一用户内唯一。",
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
    created: bool = Field(description="True if new task was created, False if deduplicated.")


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

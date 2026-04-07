"""
User Assets API Schemas: Analysis Records.

Defines request/response Pydantic models for /records endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class RecordCreateRequest(BaseModel):
    """POST /records — create/save an analysis record."""

    client_record_id: str = Field(min_length=1, max_length=64)
    source_type: str = Field(default="user_input")
    title: str | None = Field(default=None, max_length=256)
    source_text: str = Field(min_length=1)
    source_text_hash: str = Field(min_length=1, max_length=64)
    request_payload_json: dict[str, Any] = Field(default_factory=dict)
    render_scene_json: dict[str, Any] = Field(default_factory=dict)
    page_state_json: dict[str, Any] = Field(default_factory=dict)
    reading_goal: str | None = Field(default=None)
    reading_variant: str | None = Field(default=None)
    user_facing_state: str | None = Field(default=None)
    workflow_version: str | None = Field(default=None)
    schema_version: str | None = Field(default=None)
    analysis_status: str = Field(default="ready")


class RecordUpdateRequest(BaseModel):
    """PATCH /records/{id} — partial update."""

    title: str | None = Field(default=None, max_length=256)
    render_scene_json: dict[str, Any] | None = None
    page_state_json: dict[str, Any] | None = None
    user_facing_state: str | None = None
    analysis_status: str | None = None
    is_favorited: bool | None = None
    last_opened_at: datetime | None = None


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class RecordResponse(BaseModel):
    """Single analysis record."""

    id: UUID
    user_id: UUID
    client_record_id: str
    source_type: str
    title: str | None
    source_text: str
    source_text_hash: str
    request_payload_json: dict[str, Any]
    render_scene_json: dict[str, Any]
    page_state_json: dict[str, Any]
    reading_goal: str | None
    reading_variant: str | None
    user_facing_state: str | None
    workflow_version: str | None
    schema_version: str | None
    analysis_status: str
    last_opened_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordListResponse(BaseModel):
    """GET /records — paginated list."""

    items: list[RecordResponse]
    total: int
    page: int
    limit: int


class RecordUpsertResponse(BaseModel):
    """POST /records — upsert result."""

    id: UUID
    client_record_id: str
    created: bool  # True if new, False if updated
    updated_at: datetime

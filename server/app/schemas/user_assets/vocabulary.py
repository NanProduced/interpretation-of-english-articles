"""
User Assets API Schemas: Vocabulary Book.

Defines request/response Pydantic models for /vocabulary endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class VocabularyCreateRequest(BaseModel):
    """POST /vocabulary — add a word/phrase to vocabulary book."""

    client_id: str | None = Field(default=None, max_length=64)
    analysis_record_id: UUID | None = Field(default=None)
    lemma: str = Field(min_length=1, max_length=256)
    display_word: str = Field(min_length=1, max_length=256)
    phonetic: str | None = Field(default=None, max_length=256)
    part_of_speech: str | None = Field(default=None, max_length=64)
    short_meaning: str = Field(min_length=1)
    meanings_json: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    exchange: list[str] = Field(default_factory=list)
    source_provider: str = Field(default="tecd3")
    source_sentence: str | None = Field(default=None)
    source_context: str | None = Field(default=None)
    payload_json: dict[str, Any] = Field(default_factory=dict)


class VocabularyUpdateRequest(BaseModel):
    """PATCH /vocabulary/{id} — update a vocabulary entry."""

    mastery_status: str | None = Field(default=None)
    short_meaning: str | None = Field(default=None)
    payload_json: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class VocabularyResponse(BaseModel):
    """Single vocabulary entry."""

    id: UUID
    user_id: UUID
    lemma: str
    display_word: str
    phonetic: str | None
    part_of_speech: str | None
    short_meaning: str
    meanings_json: list[dict[str, Any]]
    tags: list[str]
    exchange: list[str]
    source_provider: str
    analysis_record_id: UUID | None
    source_sentence: str | None
    source_context: str | None
    mastery_status: str
    review_count: int
    last_reviewed_at: datetime | None
    payload_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VocabularyListResponse(BaseModel):
    """GET /vocabulary — paginated list."""

    items: list[VocabularyResponse]
    total: int
    page: int
    limit: int


class VocabularyUpsertResponse(BaseModel):
    """POST /vocabulary — upsert result."""

    id: UUID
    lemma: str
    created: bool  # True if new, False if updated
    updated_at: datetime

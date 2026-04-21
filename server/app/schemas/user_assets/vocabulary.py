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
# Shared Sub-models
# ---------------------------------------------------------------------------


class SourceRef(BaseModel):
    """单次收藏来源的语境记录，存储在 payload_json.source_refs 中。"""

    client_record_id: str = Field(default="", max_length=128)
    cloud_record_id: str | None = Field(default=None, max_length=128)
    source_sentence: str | None = Field(default=None)
    source_context: str | None = Field(default=None)
    source_sentence_id: str | None = Field(default=None, max_length=64)
    source_anchor_text: str | None = Field(default=None, max_length=256)
    source_occurrence: int | None = Field(default=None, ge=1)
    collected_at: str | None = Field(default=None)


class VocabularyPayload(BaseModel):
    """payload_json 的结构化模型，便于类型安全地读写扩展元数据。"""

    source_refs: list[SourceRef] = Field(default_factory=list)
    collected_forms: list[str] = Field(default_factory=list)
    audio_url: str | None = Field(default=None, max_length=512)

    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class VocabularyCreateRequest(BaseModel):
    """POST /vocabulary — add a word/phrase to vocabulary book."""

    lemma: str = Field(min_length=1, max_length=256)
    display_word: str = Field(min_length=1, max_length=256)
    phonetic: str | None = Field(default=None, max_length=256)
    part_of_speech: str | None = Field(default=None, max_length=64)
    short_meaning: str = Field(min_length=1)
    meanings_json: list[dict[str, Any]] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    exchange: list[str] = Field(default_factory=list)
    source_provider: str = Field(default="tecd3")
    dict_entry_id: int | None = Field(default=None, description="词典词条稳定引用 ID")
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
    meanings_json: list[dict[str, Any]] | None = Field(default=None)
    tags: list[str]
    exchange: list[str]
    source_provider: str
    dict_entry_id: int | None = Field(default=None, description="词典词条稳定引用 ID")
    source_sentence: str | None = Field(default=None)
    source_context: str | None = Field(default=None)
    mastery_status: str
    review_count: int
    last_reviewed_at: datetime | None
    next_review_at: datetime | None = Field(default=None, description="下一次复习时间")
    ease_factor: float = Field(default=2.5, description="易度因子，SM-2算法核心参数")
    repetitions: int = Field(default=0, description="连续成功复习次数")
    review_interval: int = Field(default=1, description="当前复习间隔（天）")
    payload_json: dict[str, Any] | None = Field(default=None)
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
    created: bool
    updated_at: datetime


# ---------------------------------------------------------------------------
# Highlights (Result Page Overlay)
# ---------------------------------------------------------------------------


class SentenceTokens(BaseModel):
    """单个句子的 token 列表，用于 highlights 请求。"""

    sentence_id: str = Field(min_length=1, max_length=64)
    tokens: list[str] = Field(min_length=1)


class VocabHighlightsRequest(BaseModel):
    """POST /vocabulary/highlights — 查询句子中已收藏的生词匹配。"""

    sentences: list[SentenceTokens] = Field(min_length=1, max_length=200)


class VocabMatchItem(BaseModel):
    """单个匹配结果：句子中某个 token 匹配到了用户生词本中的词条。"""

    vocab_id: UUID
    lemma: str
    sentence_id: str
    anchor_text: str
    occurrence: int
    mastery_status: str


class VocabHighlightsResponse(BaseModel):
    """POST /vocabulary/highlights — 匹配结果。"""

    matches: list[VocabMatchItem]


# ---------------------------------------------------------------------------
# Review System Models
# ---------------------------------------------------------------------------


class ReviewQuality(str):
    """复习质量评分，采用 SM-2 算法的 0-5 分制。

    - 0: 完全忘记 (Complete Blackout)
    - 1: 几乎忘记 (Wrong Response)
    - 2: 模糊记得 (Wrong Response, On The Tip Of The Tongue)
    - 3: 记住了 (Correct Response, With Serious Difficulty)
    - 4: 熟练掌握 (Correct Response, With Some Hesitation)
    - 5: 完全掌握 (Perfect Response)
    """

    pass


class ReviewSubmitRequest(BaseModel):
    """提交复习结果请求。"""

    vocab_id: UUID = Field(description="生词记录ID")
    quality: int = Field(ge=0, le=5, description="复习质量评分 0-5")


class ReviewSubmitResponse(BaseModel):
    """提交复习结果响应。"""

    vocab_id: UUID
    success: bool
    next_review_at: datetime | None
    new_ease_factor: float
    new_interval: int
    new_repetitions: int
    new_mastery_status: str
    quality: int
    message: str


class ReviewStatsResponse(BaseModel):
    """复习统计数据。"""

    total_vocab: int = Field(description="生词总数")
    due_today: int = Field(description="今日待复习数量")
    overdue: int = Field(description="逾期未复习数量")
    new_words: int = Field(description="新词数量（从未复习过）")
    learning: int = Field(description="学习中数量")
    mastered: int = Field(description="已掌握数量")


class DueVocabItem(BaseModel):
    """待复习生词条目。"""

    id: UUID
    lemma: str
    display_word: str
    phonetic: str | None
    part_of_speech: str | None
    short_meaning: str
    mastery_status: str
    repetitions: int
    ease_factor: float
    review_interval: int
    next_review_at: datetime | None
    source_sentence: str | None = Field(default=None)
    source_refs: list[dict[str, Any]] | None = Field(default=None, description="来源语境列表")
    meanings_json: list[dict[str, Any]] | None = Field(default=None)
    payload_json: dict[str, Any] | None = Field(default=None)


class DueVocabListResponse(BaseModel):
    """待复习单词列表响应。"""

    items: list[DueVocabItem]
    total: int
    due_type: str = Field(description="due_type: today/overdue/new")

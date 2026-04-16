"""
Feedback System API Schemas.

Defines request/response Pydantic models for /feedbacks endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FeedbackType(str, Enum):
    """反馈类型枚举"""
    RESULT_OVERALL = "result_overall"
    GRAMMAR_NOTE = "grammar_note"
    SENTENCE_ANALYSIS = "sentence_analysis"
    VOCAB_ENTRY = "vocab_entry"
    GENERAL = "general"


class FeedbackCategory(str, Enum):
    """反馈分类枚举（不满意时选择的类型）"""
    DATA_ERROR = "data_error"
    POOR_QUALITY = "poor_quality"
    TRANSLATION_WRONG = "translation_wrong"
    INCOMPLETE = "incomplete"
    IRRELEVANT = "irrelevant"
    UNCLEAR = "unclear"
    PERFORMANCE = "performance"
    UI_UX = "ui_ux"
    OTHER = "other"


class FeedbackStatus(str, Enum):
    """反馈处理状态枚举"""
    PENDING = "pending"
    REVIEWED = "reviewed"
    USED_FOR_RAG = "used_for_rag"
    DISMISSED = "dismissed"


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class ResultOverallContext(BaseModel):
    """结果页整体反馈的上下文数据"""
    source_text_preview: str | None = Field(default=None, max_length=500)
    source_text_length: int | None = None
    reading_goal: str | None = None
    reading_variant: str | None = None
    extended: bool | None = None
    user_facing_state: str | None = None
    processing_ms: int | None = None
    task_status: str | None = None
    sentence_count: int | None = None
    vocab_count: int | None = None


class AnnotationContext(BaseModel):
    """标注（语法/句式）反馈的上下文数据"""
    sentence_id: str | None = None
    sentence_text: str | None = None
    annotation_id: str | None = None
    annotation_type: str | None = None
    label: str | None = None
    content_preview: str | None = Field(default=None, max_length=500)
    source_text_preview: str | None = Field(default=None, max_length=500)


class VocabContext(BaseModel):
    """词汇卡片反馈的上下文数据"""
    lemma: str | None = None
    display_word: str | None = None
    part_of_speech: str | None = None
    short_meaning: str | None = None
    phonetic: str | None = None
    source_sentence: str | None = None
    context_preview: str | None = Field(default=None, max_length=500)


class GeneralContext(BaseModel):
    """通用反馈的上下文数据"""
    page: str | None = None
    app_version: str | None = None
    platform: str | None = None


class CreateFeedbackRequest(BaseModel):
    """POST /feedbacks — 创建反馈的请求模型"""

    feedback_type: FeedbackType = Field(description="反馈类型")
    satisfaction: bool | None = Field(default=None, description="是否满意，null 表示未评价")
    category: FeedbackCategory | None = Field(default=None, description="反馈分类（不满意时选择）")
    detail_text: str | None = Field(default=None, max_length=2000, description="用户输入的详细理由")
    analysis_record_id: UUID | None = Field(default=None, description="关联的分析记录 ID")
    context_json: dict[str, Any] = Field(default_factory=dict, description="上下文数据（根据 feedback_type 不同而不同）")
    client_metadata_json: dict[str, Any] = Field(default_factory=dict, description="客户端元数据")


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class FeedbackResponse(BaseModel):
    """单条反馈的响应模型"""

    id: UUID
    user_id: UUID
    feedback_type: str
    satisfaction: bool | None
    category: str | None
    detail_text: str | None
    analysis_record_id: UUID | None
    context_json: dict[str, Any]
    client_metadata_json: dict[str, Any]
    status: str
    admin_note: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackListResponse(BaseModel):
    """反馈列表响应模型"""

    items: list[FeedbackResponse]
    total: int
    page: int
    limit: int


class FeedbackCreateResponse(BaseModel):
    """创建反馈的响应模型"""

    id: UUID
    created: bool
    created_at: datetime

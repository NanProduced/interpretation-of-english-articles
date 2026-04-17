from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.internal.academic_drafts import (
    AcademicSentenceTranslation,
    ContentSummary,
    InterpretationNote,
    LogicNote,
    ParagraphRole,
    TermNote,
)
from app.schemas.internal.normalized import DropLogEntry


class AcademicGoalPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    term_density: int = Field(default=5, ge=1, description="每句最大术语标注数")
    logic_density: int = Field(default=2, ge=1, description="每句最大逻辑标注数")
    interpretation_density: int = Field(default=1, ge=0, description="每句最大解释标注数")
    require_paragraph_role: bool = False
    require_content_summary: bool = False
    translation_rigor: Literal["research_reading"] = "research_reading"


class AcademicNormalizedResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    term_annotations: list[TermNote] = Field(default_factory=list)
    sentence_translations: list[AcademicSentenceTranslation] = Field(default_factory=list)
    logic_notes: list[LogicNote] = Field(default_factory=list)
    interpretation_notes: list[InterpretationNote] = Field(default_factory=list)
    paragraph_roles: list[ParagraphRole] = Field(default_factory=list)
    content_summary: ContentSummary | None = None
    title: str = Field(min_length=1, description="中文标题")
    drop_log: list[DropLogEntry] = Field(default_factory=list, description="归一化阶段的删除/降级日志")

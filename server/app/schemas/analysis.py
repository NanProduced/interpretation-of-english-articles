from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.llm.types import ModelSelection
from app.schemas.common import TextSpan
from app.schemas.internal.analysis import (
    AnnotationType,
    DisplayGroup,
    DisplayMode,
    DisplayPriority,
    PedagogyLevel,
    ReadingGoal,
    ReadingVariant,
)

ANALYSIS_SCHEMA_VERSION = "1.0.0"

GOAL_VARIANT_MAP: dict[ReadingGoal, set[ReadingVariant]] = {
    "exam": {"gaokao", "cet4", "cet6", "kaoyan", "ielts", "toefl"},
    "daily_reading": {"beginner_reading", "intermediate_reading", "intensive_reading"},
    "academic": {"academic_general"},
}


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, description="待分析的原始英文文本。")
    reading_goal: ReadingGoal = Field(
        default="daily_reading",
        description="阅读目标，是讲解风格的软偏好。",
    )
    reading_variant: ReadingVariant = Field(
        default="intermediate_reading",
        description="阅读细分场景，是讲解关注点的强提示。",
    )
    source_type: Literal["user_input", "daily_article", "ocr"] = Field(
        default="user_input",
        description="文本来源类型，用于区分用户输入、每日文章或 OCR 输入。",
    )
    request_id: str | None = Field(default=None, description="可选请求标识；未提供时由后端生成。")
    model_selection: ModelSelection | None = Field(
        default=None,
        description="运行时模型路由配置，沿用现有 app/llm 体系。",
    )

    @model_validator(mode="after")
    def validate_goal_variant(self) -> AnalyzeRequest:
        allowed_variants = GOAL_VARIANT_MAP[self.reading_goal]
        if self.reading_variant not in allowed_variants:
            raise ValueError(
                "reading_variant="
                f"{self.reading_variant} does not match reading_goal={self.reading_goal}"
            )
        return self


class AnalyzeRequestMeta(BaseModel):
    request_id: str = Field(description="实际执行本次分析的请求标识。")
    source_type: Literal["user_input", "daily_article", "ocr"] = Field(description="请求来源类型。")
    reading_goal: ReadingGoal = Field(description="本次分析采用的阅读目标。")
    reading_variant: ReadingVariant = Field(description="本次分析采用的阅读细分场景。")
    profile_id: str = Field(description="后端生成的规则包标识。")


class AnalysisStatus(BaseModel):
    state: Literal["success", "failed"] = Field(description="整条 workflow 的最终状态。")
    is_degraded: bool = Field(description="是否发生了局部丢弃或降级。")
    error_code: str | None = Field(default=None, description="失败或降级时的错误码。")
    user_message: str | None = Field(default=None, description="面向用户的简洁中文提示。")


class SanitizeReport(BaseModel):
    actions: list[str] = Field(
        default_factory=list,
        description="输入清洗阶段执行的动作列表。",
    )
    removed_segment_count: int = Field(
        ge=0,
        default=0,
        description="被清洗逻辑剔除或替换的噪音片段数量。",
    )


class ArticleParagraph(BaseModel):
    paragraph_id: str = Field(description="段落稳定标识。")
    text: str = Field(description="清洗后的段落文本。")
    render_span: TextSpan = Field(description="段落在 render_text 中的绝对坐标。")
    sentence_ids: list[str] = Field(default_factory=list, description="该段落包含的句子标识列表。")


class ArticleSentence(BaseModel):
    sentence_id: str = Field(description="句子稳定标识。")
    paragraph_id: str = Field(description="所属段落标识。")
    text: str = Field(description="清洗后的句子文本。")
    sentence_span: TextSpan = Field(description="句子在 render_text 中的绝对坐标。")


class ArticleStructure(BaseModel):
    source_type: Literal["user_input", "daily_article", "ocr"] = Field(description="文本来源类型。")
    source_text: str = Field(description="用户输入的原始文本。")
    render_text: str = Field(description="清洗后可安全渲染、可定位的正文文本。")
    paragraphs: list[ArticleParagraph] = Field(
        default_factory=list,
        description="渲染正文中的段落列表。",
    )
    sentences: list[ArticleSentence] = Field(
        default_factory=list,
        description="渲染正文中的句子列表。",
    )


class BaseAnnotation(BaseModel):
    annotation_id: str = Field(description="稳定标注标识，供前端与追踪系统引用。")
    annotation_type: AnnotationType = Field(description="标注类型。")
    sentence_id: str = Field(description="该标注关联的句子标识。")
    anchor_text: str = Field(description="模型返回的锚点文本。")
    render_span: TextSpan = Field(description="该标注相对于 render_text 的绝对坐标。")
    title: str = Field(description="标注标题。")
    content: str = Field(description="面向用户的中文讲解内容。")
    pedagogy_level: PedagogyLevel = Field(description="教学层级，用于控制默认展示方式。")
    display_priority: DisplayPriority = Field(description="前端默认展示优先级。")
    display_group: DisplayGroup = Field(description="前端展示分组。")
    is_default_visible: bool = Field(description="该标注是否默认展开或高亮。")
    render_index: int = Field(ge=1, description="按 render_text 排序后的稳定渲染序号。")


class VocabularyAnnotation(BaseAnnotation):
    annotation_type: Literal["vocabulary"] = Field(
        default="vocabulary",
        description="词汇或短语类标注。",
    )


class GrammarAnnotation(BaseAnnotation):
    annotation_type: Literal["grammar"] = Field(
        default="grammar",
        description="语法讲解类标注。",
    )


class SentenceAnnotation(BaseAnnotation):
    annotation_type: Literal["sentence_note"] = Field(
        default="sentence_note",
        description="句级讲解或难句说明类标注。",
    )


class RenderMark(BaseModel):
    mark_id: str = Field(description="稳定渲染标识，供前端高亮层使用。")
    annotation_id: str = Field(description="该渲染标记关联的 annotation_id。")
    display_mode: DisplayMode = Field(description="标注在结果页中的默认展示方式。")
    display_priority: DisplayPriority = Field(description="展示优先级。")
    display_group: DisplayGroup = Field(description="展示分组。")
    render_index: int = Field(ge=1, description="按 render_text 排序后的渲染序号。")
    render_span: TextSpan = Field(description="该渲染标记对应的绝对坐标。")


class SentenceTranslation(BaseModel):
    sentence_id: str = Field(description="逐句翻译对应的句子标识。")
    translation_zh: str = Field(description="该句子的中文翻译。")


class AnalysisTranslations(BaseModel):
    sentence_translations: list[SentenceTranslation] = Field(
        default_factory=list,
        description="逐句翻译结果。",
    )
    full_translation_zh: str = Field(description="由组装阶段生成的全文中文翻译。")


class AnalysisWarning(BaseModel):
    code: str = Field(description="面向调试和前端提示的 warning code。")
    message_zh: str = Field(description="简洁中文 warning 信息。")


class AnalysisMetrics(BaseModel):
    vocabulary_count: int = Field(ge=0, description="词汇标注数量。")
    grammar_count: int = Field(ge=0, description="语法标注数量。")
    sentence_note_count: int = Field(ge=0, description="句级讲解数量。")
    render_mark_count: int = Field(ge=0, description="渲染标记数量。")
    sentence_count: int = Field(ge=0, description="正文句子数量。")
    paragraph_count: int = Field(ge=0, description="正文段落数量。")


class AnalysisResult(BaseModel):
    schema_version: Literal["1.0.0"] = Field(
        default="1.0.0",
        description="当前分析结果的 schema 版本。",
    )
    request: AnalyzeRequestMeta = Field(description="请求快照与规则包信息。")
    status: AnalysisStatus = Field(description="整条 workflow 的最终状态。")
    article: ArticleStructure = Field(description="结果页渲染所依赖的正文结构。")
    sanitize_report: SanitizeReport = Field(description="输入清洗报告。")
    vocabulary_annotations: list[VocabularyAnnotation] = Field(
        default_factory=list,
        description="高价值词汇或短语标注。",
    )
    grammar_annotations: list[GrammarAnnotation] = Field(
        default_factory=list,
        description="重点语法讲解标注。",
    )
    sentence_annotations: list[SentenceAnnotation] = Field(
        default_factory=list,
        description="句级讲解标注。",
    )
    render_marks: list[RenderMark] = Field(
        default_factory=list,
        description="结果页高亮与笔记层所需的渲染标记。",
    )
    translations: AnalysisTranslations = Field(description="逐句翻译与全文翻译结果。")
    warnings: list[AnalysisWarning] = Field(
        default_factory=list,
        description="调试与用户提示 warning 列表。",
    )
    metrics: AnalysisMetrics = Field(description="标注数量与文本结构统计。")

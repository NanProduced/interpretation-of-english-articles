from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import TextSpan

ReadingGoal = Literal["exam", "daily_reading", "academic"]
ReadingVariant = Literal[
    "gaokao",
    "cet4",
    "cet6",
    "kaoyan",
    "ielts",
    "toefl",
    "beginner_reading",
    "intermediate_reading",
    "intensive_reading",
    "academic_general",
]
TeachingStyle = Literal["exam_oriented", "plain_and_supportive", "structural_and_academic"]
TranslationStyle = Literal["exam", "natural", "academic"]
GrammarGranularity = Literal["focused", "balanced", "structural"]
VocabularyPolicy = Literal["high_value_only", "exam_priority", "academic_priority"]
DisplayMode = Literal["underline", "highlight", "inline_note", "footnote_card", "bottom_detail"]
DisplayPriority = Literal["primary", "secondary", "tertiary"]
DisplayGroup = Literal["core", "support", "advanced"]
PedagogyLevel = Literal["core", "support", "advanced"]
AnnotationType = Literal["vocabulary", "grammar", "sentence_note"]


class AnnotationBudget(BaseModel):
    vocabulary_count: int = Field(
        ge=0,
        description="建议输出的重点词汇或短语条数上限。",
    )
    grammar_count: int = Field(
        ge=0,
        description="建议输出的语法讲解条数上限。",
    )
    sentence_note_count: int = Field(
        ge=0,
        description="建议输出的句级讲解条数上限。",
    )


class PresentationPolicy(BaseModel):
    advanced_default_collapsed: bool = Field(
        description="高阶内容是否默认折叠，避免结果页在入门场景下信息过载。",
    )
    vocabulary_display_mode: DisplayMode = Field(
        description="词汇标注的默认展示方式。",
    )
    grammar_display_mode: DisplayMode = Field(
        description="语法标注的默认展示方式。",
    )
    sentence_display_mode: DisplayMode = Field(
        description="句级讲解的默认展示方式。",
    )


class UserRules(BaseModel):
    profile_id: str = Field(
        description="后端根据 reading_goal 和 reading_variant 生成的规则包标识。"
    )
    reading_goal: ReadingGoal = Field(description="阅读目标，是讲解风格的软偏好。")
    reading_variant: ReadingVariant = Field(description="阅读细分场景，是讲解关注点的强提示。")
    teaching_style: TeachingStyle = Field(description="主教学节点使用的讲解风格。")
    translation_style: TranslationStyle = Field(description="逐句翻译的风格。")
    grammar_granularity: GrammarGranularity = Field(description="语法讲解的颗粒度。")
    vocabulary_policy: VocabularyPolicy = Field(description="词汇标注的筛选策略。")
    annotation_budget: AnnotationBudget = Field(description="不同标注类型的建议输出预算。")
    presentation_policy: PresentationPolicy = Field(description="前端默认展示方式的策略集合。")


class SanitizeReport(BaseModel):
    actions: list[str] = Field(
        default_factory=list,
        description="输入清洗阶段实际执行的规范化或剔除动作。",
    )
    removed_segment_count: int = Field(
        ge=0,
        default=0,
        description="被清洗逻辑剔除或替换的噪音片段数量。",
    )


class ParagraphDraft(BaseModel):
    paragraph_id: str = Field(description="段落稳定标识。")
    text: str = Field(description="清洗后用于渲染的段落文本。")
    render_span: TextSpan = Field(description="段落在 render_text 中的绝对坐标。")
    sentence_ids: list[str] = Field(
        default_factory=list,
        description="该段落包含的句子标识列表。",
    )


class SentenceDraft(BaseModel):
    sentence_id: str = Field(description="句子稳定标识。")
    paragraph_id: str = Field(description="所属段落标识。")
    text: str = Field(description="清洗后的句子文本。")
    sentence_span: TextSpan = Field(description="句子在 render_text 中的绝对坐标。")


class PreparedInput(BaseModel):
    source_text: str = Field(description="用户输入的原始文本，用于结果页的“查看原文”模块。")
    render_text: str = Field(description="清洗后可安全渲染、可定位的正文文本。")
    paragraphs: list[ParagraphDraft] = Field(default_factory=list, description="清洗后的段落列表。")
    sentences: list[SentenceDraft] = Field(default_factory=list, description="清洗后的句子列表。")
    sanitize_report: SanitizeReport = Field(description="输入清洗报告。")
    english_ratio: float = Field(ge=0.0, le=1.0, description="render_text 中英文字符的粗略占比。")
    noise_ratio: float = Field(ge=0.0, le=1.0, description="原始输入中被视为噪音并被处理的比例。")
    text_type: Literal["article", "list", "code", "other"] = Field(
        description="本地粗判得到的文本类型。"
    )


class AnnotationDraft(BaseModel):
    sentence_id: str = Field(description="该标注关联的句子标识。")
    anchor_text: str = Field(description="模型返回的句级锚点文本，不返回全文字符坐标。")
    anchor_occurrence: int | None = Field(
        default=None,
        ge=1,
        description="当同一句中 anchor_text 多次出现时，指明要命中的第几次出现。",
    )
    title: str = Field(description="标注标题，供前端和用户快速理解该条讲解主题。")
    content: str = Field(description="简洁中文讲解内容。")
    pedagogy_level: PedagogyLevel = Field(description="教学层级，用于控制默认展示强度。")


class SentenceTranslationDraft(BaseModel):
    sentence_id: str = Field(description="逐句翻译对应的句子标识。")
    translation_zh: str = Field(description="该句子的中文翻译。")


class TeachingOutput(BaseModel):
    vocabulary_annotations: list[AnnotationDraft] = Field(
        default_factory=list,
        description="高价值词汇或短语的教学草稿。",
    )
    grammar_annotations: list[AnnotationDraft] = Field(
        default_factory=list,
        description="重点语法讲解的教学草稿。",
    )
    sentence_annotations: list[AnnotationDraft] = Field(
        default_factory=list,
        description="难句或句级讲解的教学草稿。",
    )
    sentence_translations: list[SentenceTranslationDraft] = Field(
        default_factory=list,
        description="逐句翻译结果。",
    )

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import TextSpan

ReadingGoal = Literal["exam", "daily_reading", "academic"]
ReadingVariant = Literal[
    "gaokao",
    "cet",
    "gre",
    "ielts_toefl",
    "beginner_reading",
    "intermediate_reading",
    "intensive_reading",
    "academic_general",
]
AnnotationStyle = Literal["exam_oriented", "plain_and_supportive", "structural_and_academic"]
TranslationStyle = Literal["exam", "natural", "academic"]
GrammarGranularity = Literal["focused", "balanced", "structural"]
VocabularyPolicy = Literal["high_value_only", "exam_priority", "academic_priority"]
ExamTag = Literal["gaokao", "cet", "gre", "ielts_toefl"]

BASE_MODEL_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


class UserRules(BaseModel):
    model_config = BASE_MODEL_CONFIG

    profile_id: str = Field(description="规则包ID")
    reading_goal: ReadingGoal = Field(description="阅读目标")
    reading_variant: ReadingVariant = Field(description="阅读场景")
    annotation_style: AnnotationStyle = Field(description="标注风格")
    translation_style: TranslationStyle = Field(description="翻译风格")
    grammar_granularity: GrammarGranularity = Field(description="语法颗粒度")
    vocabulary_policy: VocabularyPolicy = Field(description="词汇筛选策略")


class SanitizeReport(BaseModel):
    actions: list[str] = Field(
        default_factory=list, description="输入清洗阶段实际执行的规范化或剔除动作。"
    )
    removed_segment_count: int = Field(
        ge=0, default=0, description="被清洗逻辑剔除或替换的噪音片段数量。"
    )


class PreparedParagraph(BaseModel):
    """输入预处理后的段落。设计稿中 ArticleParagraph 用于文章结构，此处为输入准备阶段的表示。"""

    paragraph_id: str = Field(description="段落稳定标识。")
    text: str = Field(description="清洗后用于渲染的段落文本。")
    render_span: TextSpan = Field(description="段落在 render_text 中的绝对坐标。")
    sentence_ids: list[str] = Field(default_factory=list, description="该段落包含的句子标识列表。")


class PreparedSentence(BaseModel):
    """输入预处理后的句子。设计稿中 ArticleSentence 用于文章结构，此处为输入准备阶段的表示。"""

    sentence_id: str = Field(description="句子稳定标识。")
    paragraph_id: str = Field(description="所属段落标识。")
    text: str = Field(description="清洗后的句子文本。")
    sentence_span: TextSpan = Field(description="句子在 render_text 中的绝对坐标。")


class PreparedInput(BaseModel):
    source_text: str = Field(description='用户输入的原始文本，用于结果页的"查看原文"模块。')
    render_text: str = Field(description="清洗后可安全渲染、可定位的正文文本。")
    paragraphs: list[PreparedParagraph] = Field(default_factory=list, description="清洗后的段落列表。")
    sentences: list[PreparedSentence] = Field(default_factory=list, description="清洗后的句子列表。")
    sanitize_report: SanitizeReport = Field(description="输入清洗报告。")
    english_ratio: float = Field(ge=0.0, le=1.0, description="render_text 中英文字符的粗略占比。")
    noise_ratio: float = Field(ge=0.0, le=1.0, description="原始输入中被视为噪音并被处理的比例。")
    text_type: Literal["article", "list", "code", "other"] = Field(
        description="本地粗判得到的文本类型。"
    )

# ── 基础类型 ──────────────────────────────────────

class SentenceTranslation(BaseModel):
    """逐句翻译。"""

    sentence_id: str = Field(description="句子ID")
    translation_zh: str = Field(min_length=1, description="中文翻译")


class SpanRef(BaseModel):
    """语法锚点片段。"""
    text: str = Field(min_length=1, description="对应句子中的精确子串")
    occurrence: int | None = Field(
        default=None, ge=1, description="同一句中该文本第几次出现"
    )
    role: str | None = Field(default=None, description="结构角色（可选）")


class Chunk(BaseModel):
    """长难句拆解的成分块。"""
    order: int = Field(ge=1, description="阅读顺序，从1开始。")
    label: str = Field(min_length=1, description="成分名称")
    text: str = Field(min_length=1, description="对应句子中的精确子串")
    occurrence: int | None = Field(default=None, ge=1, description="同一句中该文本第几次出现")

# ── 标注组件（Discriminated Union）──────────────────

class VocabHighlight(BaseModel):
    """考试词汇高亮。只选词 + 打考试标签，不写释义（释义由前端词典 API 提供）。"""
    model_config = BASE_MODEL_CONFIG

    type: Literal["vocab_highlight"] = "vocab_highlight"
    sentence_id: str = Field(description="句子ID")
    text: str = Field(min_length=1, description="单个英文单词（不含空格）；多词表达请用 PhraseGloss")
    occurrence: int | None = Field(default=None, ge=1, description="同一句中该文本第几次出现")
    exam_tags: list[ExamTag] = Field(min_length=1, max_length=2, description="考试标签")


class PhraseGloss(BaseModel):
    """短语/搭配释义。用于词典 API 查不到整体释义的多词表达。"""
    model_config = BASE_MODEL_CONFIG

    type: Literal["phrase_gloss"] = "phrase_gloss"
    sentence_id: str = Field(description="句子ID")
    text: str = Field(min_length=1, description="原文短语（两个词及以上，含空格）")
    occurrence: int | None = Field(default=None, ge=1, description="同一句中该文本第几次出现")
    phrase_type: Literal["collocation", "phrasal_verb", "idiom", "proper_noun", "compound"] = Field(
        description="短语类型"
    )
    zh: str = Field(min_length=1, description="中文释义")


class ContextGloss(BaseModel):
    """语境特殊义或是网络用语。仅在词典释义无法准确表达当前语境含义时使用。"""
    model_config = BASE_MODEL_CONFIG

    type: Literal["context_gloss"] = "context_gloss"
    sentence_id: str = Field(description="句子ID")
    text: str = Field(min_length=1, description="原文词汇")
    occurrence: int | None = Field(default=None, ge=1, description="同一句中该文本第几次出现")
    gloss: str = Field(min_length=1, description="当前语境下的特殊含义")
    reason: str = Field(min_length=1, description="补充原因")


class GrammarNote(BaseModel):
    """语法旁注。支持多段锚点（spans）处理不连续语法结构。"""
    model_config = BASE_MODEL_CONFIG

    type: Literal["grammar_note"] = "grammar_note"
    sentence_id: str = Field(description="句子ID")
    spans: list[SpanRef] = Field(min_length=1, max_length=4, description="语法锚点片段")
    label: str = Field(min_length=1, description="语法点名称")
    note_zh: str = Field(min_length=1, description="中文说明")


class SentenceAnalysis(BaseModel):
    """长难句拆解。仅用于含嵌套从句或复杂并列结构的真正长难句。"""
    model_config = BASE_MODEL_CONFIG

    type: Literal["sentence_analysis"] = "sentence_analysis"
    sentence_id: str = Field(description="句子ID")
    label: str = Field(min_length=1, description="句型概述")
    analysis_zh: str = Field(min_length=1, description="中文解析，说明句子主干、层次关系和理解难点")
    chunks: list[Chunk] = Field(min_length=2, max_length=8, description="按阅读顺序拆解的句子成分")


Annotation = Annotated[
    VocabHighlight | PhraseGloss | ContextGloss | GrammarNote | SentenceAnalysis,
    Field(discriminator="type"),
]


class AnnotationOutput(BaseModel):
    """LLM 生成的 annotation 结果（含全量逐句翻译）。"""

    model_config = BASE_MODEL_CONFIG

    annotations: list[Annotation] = Field(description="结构化标注列表")
    sentence_translations: list[SentenceTranslation] = Field(description="全量逐句翻译")

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


class SentenceTranslation(BaseModel):
    """逐句翻译。设计稿 v2.1 节 18.1 定义为 SentenceTranslation。"""

    sentence_id: str = Field(description="句子ID")
    translation_zh: str = Field(min_length=1, max_length=220, description="中文翻译")


class SpanRef(BaseModel):
    text: str = Field(min_length=1, max_length=80, description="锚点文本")
    occurrence: int | None = Field(
        default=None, ge=1, description="重复文本时的命中序号"
    )
    role: str | None = Field(default=None, description="结构角色")


class Chunk(BaseModel):
    order: int = Field(ge=1, description="顺序")
    label: str = Field(min_length=1, max_length=24, description="成分名称")
    text: str = Field(min_length=1, max_length=120, description="句中原文片段")
    occurrence: int | None = Field(default=None, ge=1, description="重复文本时的命中序号")


class VocabHighlight(BaseModel):
    model_config = BASE_MODEL_CONFIG

    type: Literal["vocab_highlight"] = "vocab_highlight"
    sentence_id: str = Field(description="句子ID")
    text: str = Field(min_length=1, max_length=40, description="目标词")
    occurrence: int | None = Field(default=None, ge=1, description="重复文本时的命中序号")
    exam_tags: list[ExamTag] = Field(min_length=1, max_length=2, description="考试标签")


class PhraseGloss(BaseModel):
    model_config = BASE_MODEL_CONFIG

    type: Literal["phrase_gloss"] = "phrase_gloss"
    sentence_id: str = Field(description="句子ID")
    text: str = Field(min_length=1, max_length=80, description="目标短语")
    occurrence: int | None = Field(default=None, ge=1, description="重复文本时的命中序号")
    phrase_type: Literal["collocation", "phrasal_verb", "idiom", "proper_noun", "compound"] = Field(
        description="短语类型"
    )
    zh: str = Field(min_length=1, max_length=40, description="中文释义")


class ContextGloss(BaseModel):
    model_config = BASE_MODEL_CONFIG

    type: Literal["context_gloss"] = "context_gloss"
    sentence_id: str = Field(description="句子ID")
    text: str = Field(min_length=1, max_length=40, description="目标词")
    occurrence: int | None = Field(default=None, ge=1, description="重复文本时的命中序号")
    gloss: str = Field(min_length=1, max_length=40, description="语境义")
    reason: str = Field(min_length=1, max_length=100, description="补充原因")


class GrammarNote(BaseModel):
    model_config = BASE_MODEL_CONFIG

    type: Literal["grammar_note"] = "grammar_note"
    sentence_id: str = Field(description="句子ID")
    spans: list[SpanRef] = Field(min_length=1, max_length=4, description="语法锚点")
    label: str = Field(min_length=1, max_length=24, description="语法点")
    note_zh: str = Field(min_length=1, max_length=120, description="中文说明")


class SentenceAnalysis(BaseModel):
    model_config = BASE_MODEL_CONFIG

    type: Literal["sentence_analysis"] = "sentence_analysis"
    sentence_id: str = Field(description="句子ID")
    label: str = Field(min_length=1, max_length=24, description="句型概述")
    teach: str = Field(min_length=1, max_length=300, description="中文讲解")
    chunks: list[Chunk] = Field(min_length=2, max_length=8, description="拆句片段")


Annotation = Annotated[
    VocabHighlight | PhraseGloss | ContextGloss | GrammarNote | SentenceAnalysis,
    Field(discriminator="type"),
]


class AnnotationOutput(BaseModel):
    """LLM 生成的 annotation 结果（含全量逐句翻译）。设计稿 v2.1 节 18.1 定义。"""

    model_config = BASE_MODEL_CONFIG

    annotations: list[Annotation] = Field(description="结构化标注列表")
    sentence_translations: list[SentenceTranslation] = Field(description="全量逐句翻译")

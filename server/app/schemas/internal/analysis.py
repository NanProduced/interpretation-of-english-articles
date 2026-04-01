from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, Field

from app.schemas.common import TextSpan

# === 保留的 V1 类型（prepare_input/derive_user_rules 使用）===

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
    source_text: str = Field(description='用户输入的原始文本，用于结果页的"查看原文"模块。')
    render_text: str = Field(description="清洗后可安全渲染、可定位的正文文本。")
    paragraphs: list[ParagraphDraft] = Field(default_factory=list, description="清洗后的段落列表。")
    sentences: list[SentenceDraft] = Field(default_factory=list, description="清洗后的句子列表。")
    sanitize_report: SanitizeReport = Field(description="输入清洗报告。")
    english_ratio: float = Field(ge=0.0, le=1.0, description="render_text 中英文字符的粗略占比。")
    noise_ratio: float = Field(ge=0.0, le=1.0, description="原始输入中被视为噪音并被处理的比例。")
    text_type: Literal["article", "list", "code", "other"] = Field(
        description="本地粗判得到的文本类型。"
    )


class SentenceTranslationDraft(BaseModel):
    sentence_id: str = Field(description="逐句翻译对应的句子标识。")
    translation_zh: str = Field(description="该句子的中文翻译。")


# === V2 锚点模型 ===

TextAnchorKind = Literal["text"]
MultiTextAnchorKind = Literal["multi_text"]


class TextAnchor(BaseModel):
    """单段文本锚点"""
    kind: TextAnchorKind = Field(default="text", description="锚点类型为单段文本")
    sentence_id: str = Field(description="所属句子标识")
    anchor_text: str = Field(description="锚点文本，必须直接摘自对应句子")
    occurrence: int | None = Field(
        default=None,
        ge=1,
        description="当同一句中 anchor_text 多次出现时，指明要命中的第几次出现",
    )


class MultiTextPart(BaseModel):
    """多段锚点的一个部分"""
    anchor_text: str = Field(description="该部分的锚点文本")
    occurrence: int | None = Field(
        default=None,
        ge=1,
        description="当同一句中该部分文本多次出现时，指明要命中的第几次出现",
    )
    role: str | None = Field(
        default=None,
        description="角色标识，如 'part1', 'part2'",
    )


class MultiTextAnchor(BaseModel):
    """多段文本锚点（用于 so...that, not only...but also 等不连续结构）"""
    kind: MultiTextAnchorKind = Field(default="multi_text", description="锚点类型为多段文本")
    sentence_id: str = Field(description="所属句子标识")
    parts: list[MultiTextPart] = Field(
        default_factory=list,
        description="多段锚点的各部分",
    )




# === V2 标注模型 ===

InlineMarkTone = Literal["info", "focus", "exam", "phrase", "grammar"]
InlineMarkRenderType = Literal["background", "underline"]


class InlineMarkDraft(BaseModel):
    """V2 行内标注草稿"""
    anchor: Union[TextAnchor, MultiTextAnchor] = Field(description="锚点定位")
    tone: InlineMarkTone = Field(
        description="标注语气/类型：info(蓝色)/focus(橙色)/exam(红色)/phrase(紫色)/grammar(绿色)"
    )
    render_type: InlineMarkRenderType = Field(
        description="渲染类型：background(背景高亮)/underline(下划线)"
    )
    clickable: bool = Field(
        description="clickable=true 时点击进入词典弹层"
    )
    ai_note: str | None = Field(
        default=None,
        description="AI 补充说明，点击 popup 后显示在 AI Tab",
    )
    lookup_text: str | None = Field(
        default=None,
        description="要查询的文本，优先于 anchor_text 用于查词",
    )
    lookup_kind: Literal["word", "phrase"] | None = Field(
        default=None,
        description="查询类型",
    )
    ai_title: str | None = Field(
        default=None,
        description="AI 补充标题",
    )
    ai_body: str | None = Field(
        default=None,
        description="AI 补充正文",
    )


# === V2 句尾入口 ===

SentenceEntryType = Literal["grammar", "sentence_analysis", "context"]


class SentenceEntryDraft(BaseModel):
    """V2 句尾入口草稿"""
    sentence_id: str = Field(description="关联的句子标识")
    label: str = Field(description="Chip 显示文案：'语法'/'句解'/'语境'")
    entry_type: SentenceEntryType = Field(description="入口类型")
    title: str | None = Field(
        default=None,
        description="详情面板标题，默认使用 label",
    )
    content: str = Field(
        description="详情内容，支持 Markdown 格式（**粗体**, *斜体*, `行内代码`, - 列表）"
    )


# === V2 段间卡片 ===

class CardDraft(BaseModel):
    """V2 段间卡片草稿"""
    after_sentence_id: str = Field(description="插入位置后的句子标识")
    title: str = Field(description="卡片标题")
    content: str = Field(
        description="卡片内容，支持 Markdown 格式",
    )


# === V2 Teaching Output ===

class TeachingOutput(BaseModel):
    """V2 统一输出：替代 V1 的 vocabulary/grammar/sentence 三数组"""
    inline_marks: list[InlineMarkDraft] = Field(
        default_factory=list,
        description="行内标注：词汇/短语/语法高亮",
    )
    sentence_entries: list[SentenceEntryDraft] = Field(
        default_factory=list,
        description="句尾入口：语法/句解/语境",
    )
    cards: list[CardDraft] = Field(
        default_factory=list,
        description="段间卡片：重型解释卡片",
    )
    sentence_translations: list[SentenceTranslationDraft] = Field(
        default_factory=list,
        description="逐句翻译",
    )

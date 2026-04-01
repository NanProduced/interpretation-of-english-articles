from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, Field

from app.llm.types import ModelSelection
from app.schemas.common import TextSpan
from app.schemas.internal.analysis import (
    ReadingGoal,
    ReadingVariant,
)

ANALYSIS_SCHEMA_VERSION = "2.0.0"

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

    def model_post_init(self, _):
        allowed_variants = GOAL_VARIANT_MAP[self.reading_goal]
        if self.reading_variant not in allowed_variants:
            raise ValueError(
                "reading_variant="
                f"{self.reading_variant} does not match reading_goal={self.reading_goal}"
            )


class AnalyzeRequestMeta(BaseModel):
    request_id: str = Field(description="实际执行本次分析的请求标识。")
    source_type: Literal["user_input", "daily_article", "ocr"] = Field(description="请求来源类型。")
    reading_goal: ReadingGoal = Field(description="本次分析采用的阅读目标。")
    reading_variant: ReadingVariant = Field(description="本次分析采用的阅读细分场景。")
    profile_id: str = Field(description="后端生成的规则包标识。")


# === V2 Article Structure ===

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


# === V2 Translation ===

class TranslationItem(BaseModel):
    sentence_id: str = Field(description="逐句翻译对应的句子标识。")
    translation_zh: str = Field(description="该句子的中文翻译。")


# === V2 Inline Marks ===

InlineMarkTone = Literal["info", "focus", "exam", "phrase", "grammar"]
InlineMarkRenderType = Literal["background", "underline"]


class InlineMarkAnchorText(BaseModel):
    """单段文本锚点"""
    kind: Literal["text"] = Field(default="text", description="锚点类型为单段文本")
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


class InlineMarkAnchorMultiText(BaseModel):
    """多段文本锚点（用于 so...that, not only...but also 等不连续结构）"""
    kind: Literal["multi_text"] = Field(default="multi_text", description="锚点类型为多段文本")
    sentence_id: str = Field(description="所属句子标识")
    parts: list[MultiTextPart] = Field(
        default_factory=list,
        description="多段锚点的各部分",
    )


InlineMarkAnchor = Union[InlineMarkAnchorText, InlineMarkAnchorMultiText]


class InlineMark(BaseModel):
    """V2 行内标注 - 词汇/短语/语法高亮"""
    id: str = Field(description="稳定标注标识，供前端与追踪系统引用。")
    anchor: InlineMarkAnchor = Field(description="锚点定位")
    tone: InlineMarkTone = Field(
        description="标注语气/类型：info(蓝色)/focus(橙色)/exam(红色)/phrase(紫色)/grammar(绿色)"
    )
    render_type: InlineMarkRenderType = Field(
        description="渲染类型：background(背景高亮)/underline(下划线)"
    )
    clickable: bool = Field(
        default=False,
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


# === V2 Sentence Entries ===

SentenceEntryType = Literal["grammar", "sentence_analysis", "context"]


class SentenceEntry(BaseModel):
    """V2 句尾入口 - 语法/句解/语境"""
    id: str = Field(description="稳定入口标识。")
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


# === V2 Cards ===

class AnalysisCard(BaseModel):
    """V2 段间卡片 - 重型解释卡片"""
    id: str = Field(description="稳定卡片标识。")
    after_sentence_id: str = Field(description="插入位置后的句子标识")
    title: str = Field(description="卡片标题")
    content: str = Field(
        description="卡片内容，支持 Markdown 格式",
    )


# === V2 Render Scene Model ===

class RenderSceneModel(BaseModel):
    """V2 统一渲染模型 - 替代 V1 AnalysisResult"""
    schema_version: Literal["2.0.0"] = Field(
        default="2.0.0",
        description="当前分析结果的 schema 版本。",
    )
    request: AnalyzeRequestMeta = Field(description="请求快照与规则包信息。")
    article: ArticleStructure = Field(description="结果页渲染所依赖的正文结构。")
    translations: list[TranslationItem] = Field(
        default_factory=list,
        description="逐句翻译结果。",
    )
    inline_marks: list[InlineMark] = Field(
        default_factory=list,
        description="行内标注：词汇/短语/语法高亮",
    )
    sentence_entries: list[SentenceEntry] = Field(
        default_factory=list,
        description="句尾入口：语法/句解/语境",
    )
    cards: list[AnalysisCard] = Field(
        default_factory=list,
        description="段间卡片：重型解释卡片",
    )
    warnings: list[dict[str, str]] = Field(
        default_factory=list,
        description="警告信息列表。",
    )

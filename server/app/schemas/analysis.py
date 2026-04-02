from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.llm.types import ModelSelection
from app.schemas.common import TextSpan
from app.schemas.internal.analysis import ReadingGoal, ReadingVariant

ANALYSIS_SCHEMA_VERSION = "2.1.0"

GOAL_VARIANT_MAP: dict[ReadingGoal, set[ReadingVariant]] = {
    "exam": {"gaokao", "cet", "gre", "ielts_toefl"},
    "daily_reading": {"beginner_reading", "intermediate_reading", "intensive_reading"},
    "academic": {"academic_general"},
}


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, description="待分析的原始英文文本。")
    reading_goal: ReadingGoal = Field(
        default="daily_reading",
        description="阅读目标，讲解风格的软偏好。",
    )
    reading_variant: ReadingVariant = Field(
        default="intermediate_reading",
        description="阅读细分场景，讲解关注点的强提示。",
    )
    source_type: Literal["user_input", "daily_article", "ocr"] = Field(
        default="user_input",
        description="文本来源类型。",
    )
    request_id: str | None = Field(default=None, description="可选请求标识。")
    model_selection: ModelSelection | None = Field(default=None, description="运行时模型路由配置。")

    def model_post_init(self, __context__: Any) -> None:
        allowed_variants = GOAL_VARIANT_MAP[self.reading_goal]
        if self.reading_variant not in allowed_variants:
            raise ValueError(
                f"reading_variant={self.reading_variant} does not match "
                f"reading_goal={self.reading_goal}"
            )


class AnalyzeRequestMeta(BaseModel):
    request_id: str = Field(description="实际执行本次分析的请求标识。")
    source_type: Literal["user_input", "daily_article", "ocr"] = Field(description="请求来源类型。")
    reading_goal: ReadingGoal = Field(description="本次分析采用的阅读目标。")
    reading_variant: ReadingVariant = Field(description="本次分析采用的阅读细分场景。")
    profile_id: str = Field(description="后端生成的规则包标识。")


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
    paragraphs: list[ArticleParagraph] = Field(default_factory=list, description="段落列表。")
    sentences: list[ArticleSentence] = Field(default_factory=list, description="句子列表。")


class TranslationItem(BaseModel):
    sentence_id: str = Field(description="逐句翻译对应的句子标识。")
    translation_zh: str = Field(description="该句子的中文翻译。")


InlineMarkRenderType = Literal["background", "underline"]
VisualTone = Literal["vocab", "phrase", "context", "grammar"]


class InlineGlossary(BaseModel):
    zh: str | None = Field(default=None, description="中文释义")
    gloss: str | None = Field(default=None, description="语境义")
    reason: str | None = Field(default=None, description="为什么词典义不够好")


class TextAnchor(BaseModel):
    kind: Literal["text"] = Field(default="text", description="锚点类型为单段文本")
    sentence_id: str = Field(description="所属句子标识")
    anchor_text: str = Field(description="锚点文本，必须直接摘自对应句子")
    occurrence: int | None = Field(
        default=None, ge=1, description="同一句中 anchor_text 多次出现时，指明要命中的第几次"
    )


class SpanRefPart(BaseModel):
    anchor_text: str = Field(description="该部分的锚点文本")
    occurrence: int | None = Field(
        default=None, ge=1, description="同句中该部分文本多次出现时，指明要命中的第几次"
    )
    role: str | None = Field(default=None, description="结构角色")


class MultiTextAnchor(BaseModel):
    kind: Literal["multi_text"] = Field(default="multi_text", description="锚点类型为多段文本")
    sentence_id: str = Field(description="所属句子标识")
    parts: list[SpanRefPart] = Field(default_factory=list, description="多段锚点的各部分")


InlineMarkAnchor = TextAnchor | MultiTextAnchor


class InlineMark(BaseModel):
    id: str = Field(description="稳定标注标识，供前端与追踪系统引用。")
    annotation_type: Literal[
        "vocab_highlight", "phrase_gloss", "context_gloss", "grammar_note"
    ] = Field(description="语义来源，用于前端识别")
    anchor: InlineMarkAnchor = Field(description="锚点定位")
    render_type: InlineMarkRenderType = Field(description="渲染类型：background/underline")
    visual_tone: VisualTone = Field(description="渲染语义：vocab/phrase/context/grammar")
    clickable: bool = Field(description="是否可点击查询")
    lookup_text: str | None = Field(default=None, description="词典查询文本")
    lookup_kind: Literal["word", "phrase"] | None = Field(default=None, description="词典查询类型")
    glossary: InlineGlossary | None = Field(default=None, description="LLM 附加说明")


class SentenceEntry(BaseModel):
    id: str = Field(description="稳定入口标识。")
    sentence_id: str = Field(description="关联的句子标识")
    entry_type: Literal["grammar_note", "sentence_analysis"] = Field(description="入口类型")
    label: str = Field(description="Chip 显示文案")
    title: str | None = Field(default=None, description="详情面板标题，默认使用 label")
    content: str = Field(
        default="",
        description="详情内容，支持 Markdown 格式（**粗体**, *斜体*, `行内代码`, - 列表）",
    )


class Warning(BaseModel):
    code: str = Field(description="稳定错误码，如 'anchor_resolve_failed'")
    level: Literal["info", "warning", "error"] = Field(description="前端展示级别")
    message: str = Field(description="面向日志与调试的可读信息")
    sentence_id: str | None = Field(default=None, description="关联句子（可选）")
    annotation_id: str | None = Field(default=None, description="关联标注（可选）")


class RenderSceneModel(BaseModel):
    schema_version: Literal["3.0.0"] = Field(
        default="3.0.0", description="当前分析结果的 schema 版本。"
    )
    request: AnalyzeRequestMeta = Field(description="请求快照与规则包信息。")
    article: ArticleStructure = Field(description="结果页渲染所依赖的正文结构。")
    translations: list[TranslationItem] = Field(default_factory=list, description="逐句翻译结果。")
    inline_marks: list[InlineMark] = Field(default_factory=list, description="行内标注。")
    sentence_entries: list[SentenceEntry] = Field(default_factory=list, description="句尾入口。")
    warnings: list[Warning] = Field(default_factory=list, description="渲染与校验告警。")

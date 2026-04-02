from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.internal.analysis import (
    BASE_MODEL_CONFIG,
    Chunk,
    ContextGloss,
    ExamTag,
    GrammarNote,
    PhraseGloss,
    SentenceAnalysis,
    SentenceTranslation,
    SpanRef,
    VocabHighlight,
)


class VocabularyDraft(BaseModel):
    """Vocabulary agent 产出的标注草案。

    包含 vocab_highlight、phrase_gloss、context_gloss 三类词汇维度标注。
    设计原则：
    - 不负责语法说明、长难句拆解、逐句翻译
    - 允许漏标，不允许大面积低价值误标
    """

    model_config = BASE_MODEL_CONFIG

    vocab_highlights: list[VocabHighlight] = Field(
        default_factory=list,
        description="考试词汇高亮列表",
    )
    phrase_glosses: list[PhraseGloss] = Field(
        default_factory=list,
        description="短语/搭配释义列表",
    )
    context_glosses: list[ContextGloss] = Field(
        default_factory=list,
        description="语境特殊义标注列表",
    )


class GrammarDraft(BaseModel):
    """Grammar agent 产出的标注草案。

    包含 grammar_note、sentence_analysis 两类结构维度标注。
    设计原则：
    - 不负责词汇标注、词典查语、逐句翻译
    - 优先覆盖显著复杂句，不追求数量
    - sentence_analysis.chunks 降级为可选增强字段
    """

    model_config = BASE_MODEL_CONFIG

    grammar_notes: list[GrammarNote] = Field(
        default_factory=list,
        description="语法旁注列表",
    )
    sentence_analyses: list[SentenceAnalysis] = Field(
        default_factory=list,
        description="长难句拆解列表（chunks 为可选）",
    )


class TranslationDraft(BaseModel):
    """Translation agent 产出的翻译草案。

    设计原则：
    - 逐句翻译完整优先于风格花哨
    - 独立完成，不依赖 annotation 链路
    - 缺失应有明确 warning，不允许静默吞掉
    """

    model_config = BASE_MODEL_CONFIG

    sentence_translations: list[SentenceTranslation] = Field(
        default_factory=list,
        description="全量逐句翻译",
    )

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.internal.analysis import (
    BASE_MODEL_CONFIG,
    DocumentSummary,
    InterpretationNote,
    LogicNote,
    ParagraphRole,
    SentenceTranslation,
    TermNote,
)


class TermDraft(BaseModel):
    """术语理解 agent 产出的标注草案。

    包含 term_note 类型的术语/概念标注。
    设计原则：
    - 聚焦学术文本中的专业术语、缩写、变量、方法名、概念对立
    - 帮助用户快速理解专业词汇的含义
    """

    model_config = BASE_MODEL_CONFIG

    term_notes: list[TermNote] = Field(
        default_factory=list,
        description="术语/概念标注列表",
    )


class LogicDraft(BaseModel):
    """逻辑结构 agent 产出的标注草案。

    包含 logic_note 类型的逻辑关系标注。
    设计原则：
    - 聚焦论证结构和推理过程
    - 标注转折、让步、限定、因果、对比、假设、结论等逻辑关系
    """

    model_config = BASE_MODEL_CONFIG

    logic_notes: list[LogicNote] = Field(
        default_factory=list,
        description="逻辑关系标注列表",
    )


class InterpretationDraft(BaseModel):
    """解释性理解 agent 产出的标注草案。

    包含 interpretation_note 类型的解释性理解标注。
    设计原则：
    - 解释"这句话真正想表达什么"
    - 说明"为什么不能只按字面直译理解"
    - 这是 academic 模式的核心输出之一
    """

    model_config = BASE_MODEL_CONFIG

    interpretation_notes: list[InterpretationNote] = Field(
        default_factory=list,
        description="解释性理解标注列表",
    )


class StructureDraft(BaseModel):
    """结构分析 agent 产出的标注草案。

    包含 paragraph_role 和 document_summary。
    设计原则：
    - 标注段落功能（定义、背景、问题提出、方法、证据、结果、限制、过渡等）
    - 提供全文综合摘要
    - 帮助用户快速把握论文结构和论证脉络
    """

    model_config = BASE_MODEL_CONFIG

    paragraph_roles: list[ParagraphRole] = Field(
        default_factory=list,
        description="段落功能标注列表",
    )
    document_summary: DocumentSummary | None = Field(
        default=None,
        description="全文综合摘要",
    )


class AcademicTranslationDraft(BaseModel):
    """Academic 模式的翻译草案。

    与 learning 模式类似，但翻译风格更偏向学术化。
    """

    model_config = BASE_MODEL_CONFIG

    title: str = Field(
        min_length=1,
        max_length=80,
        description="基于全文内容生成的中文标题，用于历史记录展示。",
    )
    sentence_translations: list[SentenceTranslation] = Field(
        default_factory=list,
        description="全量逐句翻译",
    )

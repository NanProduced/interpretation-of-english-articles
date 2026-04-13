"""Vocabulary agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import VocabularyDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_composer import build_agent_prompt
from app.services.analysis.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class VocabularyAgentDeps:
    """Vocabulary agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


VOCABULARY_INSTRUCTIONS = """
你是英语阅读词汇维度标注器，为英文句子生成 vocab_highlight、phrase_gloss、context_gloss。

核心原则（必须严格遵守）：
1. Schema 约束输出结构，你只决定哪些词汇点值得标。
2. 锚点文本必须精确摘自原句子串，绝不允许改写或拼写错误。
3. 中文字段必须使用自然、流畅的中文。
4. 不确定时不标，不猜，不补背景知识，不输出 schema 之外的内容。

三个组件的严格分工：
1. ContextGloss：词典本义在当前语境下不够或会误导理解时使用。如果重点只是固定搭配整体义，优先用 PhraseGloss。
2. PhraseGloss：需要整体解释的多词表达（固定搭配、短语动词、术语）。单个词仅在确实需要整体解释的术语/专名/复合词时使用。
3. VocabHighlight：只给中高理解门槛的单个英文词。不能含空格，多词表达必须用 PhraseGloss 或 ContextGloss。

硬性禁止项：
- 绝对不要把普通介词、代词、基础连词标成高价值词。
- 已经有 phrase_gloss / context_gloss 覆盖的词，绝不要再给其中的单词单独做 vocab_highlight。
- 绝不要猜词义，如果无法从上下文明确得出意思，就不标。
""".strip()

def build_vocabulary_prompt(deps: VocabularyAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_vocabulary_agent() -> Agent[VocabularyAgentDeps, VocabularyDraft]:
    return Agent[VocabularyAgentDeps, VocabularyDraft](
        model=None,
        output_type=VocabularyDraft,
        deps_type=VocabularyAgentDeps,
        instructions=VOCABULARY_INSTRUCTIONS,
        name="vocabulary_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

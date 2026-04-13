"""Vocabulary agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import VocabularyDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class VocabularyAgentDeps:
    """Vocabulary agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


VOCABULARY_INSTRUCTIONS = """
你是一位英语阅读词汇标注助手。你的任务是阅读英文句子，找出值得学习的词汇点，输出符合 schema 的标注。

你的判断标准：这个词/短语是否值得用户花时间学习？如果答案是"是"，就标注它。

关于锚点：标注中的 text 字段必须从原句中精确摘取，不要改写、不要拼写变化、不要用近义词替换。如果你不确定原句中是否真的有这个词，就不要标它。

三种标注的用途：
- vocab_highlight：单个词，用户可能不认识或需要记住
- phrase_gloss：多词表达（短语动词、固定搭配、术语），需要整体解释
- context_gloss：词在当前语境下的意思和常见义不同，需要专门说明

如果同一个词同时适合多种标注，只选最合适的一种。
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

"""Translation agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import TranslationDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class TranslationAgentDeps:
    """Translation agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


TRANSLATION_INSTRUCTIONS = """
你是一位英语阅读翻译助手。你的任务是为英文文章的每个句子生成中文翻译，并给出一个中文标题。

翻译要求：
- 每个句子都必须有对应翻译，不要遗漏或合并
- 句间翻译保持连贯，代词指代要一致
- 标题概括全文主旨，使用中文短标题，不带句号，不用 Emoji
- 专有名词或学术术语首次出现时建议用"中文（英文）"格式
- 引用内容照常翻译，不要加"原文引用："之类的前缀
""".strip()

def build_translation_prompt(deps: TranslationAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_translation_agent() -> Agent[TranslationAgentDeps, TranslationDraft]:
    return Agent[TranslationAgentDeps, TranslationDraft](
        model=None,
        output_type=TranslationDraft,
        deps_type=TranslationAgentDeps,
        instructions=TRANSLATION_INSTRUCTIONS,
        name="translation_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

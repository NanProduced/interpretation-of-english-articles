"""Grammar agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import GrammarDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class GrammarAgentDeps:
    """Grammar agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


GRAMMAR_INSTRUCTIONS = """
你是一位英语阅读结构标注助手。你的任务是阅读英文句子，找出值得讲解的结构点，输出 grammar_note 或 sentence_analysis。

你的判断标准：根据用户的水平或关注点帮助用户标注有价值的语法点。如果用户不看你的讲解也能读懂，就不需要标。

关于锚点：spans 和 chunks 中的 text 必须从原句中精确摘取，不要改写。

两种标注的用途：
- grammar_note：讲解一个局部语法点，帮用户理解"这里为什么这样写"或"这个结构怎么用"
- sentence_analysis：拆解复杂句的信息层次，帮用户看清"这句话应该怎么读"，必须输出 2-6 个 chunks

简单句不需要任何标注。
""".strip()

def build_grammar_prompt(deps: GrammarAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_grammar_agent() -> Agent[GrammarAgentDeps, GrammarDraft]:
    return Agent[GrammarAgentDeps, GrammarDraft](
        model=None,
        output_type=GrammarDraft,
        deps_type=GrammarAgentDeps,
        instructions=GRAMMAR_INSTRUCTIONS,
        name="grammar_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

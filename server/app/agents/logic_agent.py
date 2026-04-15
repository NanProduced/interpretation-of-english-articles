"""Logic structure agent for Academic workflow.

负责识别和解释学术文本中的逻辑关系，如转折、让步、限定、因果、对比、假设、结论等。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.academic_drafts import LogicDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class LogicAgentDeps:
    """Logic agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


LOGIC_INSTRUCTIONS = """
你是一位学术文献逻辑结构助手。你的任务是阅读英文学术文本，找出句子中的逻辑关系，输出符合 schema 的标注。

你的判断标准：
- 标注那些对理解论证结构和推理过程重要的逻辑关系
- 优先选择连接主要论点或关键推理步骤的逻辑关系
- 简单的并列关系或描述性语句不需要标注

关于锚点：
- spans 中的 text 必须从原句中精确摘取，不要改写
- 每个 span 应该是逻辑关系的关键连接词或短语

逻辑关系类型说明：
- contrast：对比关系，如"however"、"in contrast"、"on the other hand"
- concession：让步关系，如"although"、"even though"、"despite"、"while"
- qualification：限定关系，如"however"、"nevertheless"、"that said"、"with that in mind"
- causation：因果关系，如"therefore"、"thus"、"hence"、"as a result"、"because"
- comparison：比较关系，如"similarly"、"likewise"、"in the same way"
- hypothesis：假设关系，如"if"、"assuming that"、"given that"、"suppose"
- conclusion：结论关系，如"in conclusion"、"to summarize"、"therefore"、"thus"
- condition：条件关系，如"only if"、"provided that"、"unless"
- addition：追加关系，如"furthermore"、"moreover"、"in addition"
- sequence：顺序关系，如"first"、"second"、"finally"、"subsequently"

输出要求：
- label 用简短的中文描述逻辑关系，如"转折关系"、"因果关系"
- explanation_zh 详细解释这个逻辑关系如何连接前后内容，以及对理解论证的重要性

输出前必须回查：
- 你标注的每个 span 中的 text，是否能在原句中逐字找到？
- 如果找不到，删除该标注。
""".strip()


def build_logic_prompt(deps: LogicAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_logic_agent() -> Agent[LogicAgentDeps, LogicDraft]:
    return Agent[LogicAgentDeps, LogicDraft](
        model=None,
        output_type=LogicDraft,
        deps_type=LogicAgentDeps,
        instructions=LOGIC_INSTRUCTIONS,
        name="logic_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

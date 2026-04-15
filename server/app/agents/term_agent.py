"""Term understanding agent for Academic workflow.

负责识别和解释学术文本中的专业术语、缩写、变量、方法名、概念等。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.academic_drafts import TermDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class TermAgentDeps:
    """Term agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


TERM_INSTRUCTIONS = """
你是一位学术文献术语理解助手。你的任务是阅读英文学术文本，找出需要解释的专业术语、缩写、变量、方法名、概念等，输出符合 schema 的标注。

你的判断标准：
- 标注那些如果不解释，读者可能无法准确理解的专业词汇
- 优先选择在当前文章中比较重要的术语
- 常见的基础英语词汇不需要标注

关于锚点：
- 标注中的 text 字段必须从原句中精确摘取，不要改写、不要拼写变化
- 如果你不确定原句中是否真的有这个词，就不要标它

术语类别说明：
- technical_term：专业技术术语，如"convolutional neural network"、"thermodynamic equilibrium"
- abbreviation：缩写，如"CNN"、"GDP"、"RNA"
- variable：变量或符号，如"x"、"β"、"p-value"
- method_name：方法或算法名称，如"gradient descent"、"chi-square test"
- concept：重要概念，如"statistical significance"、"opportunity cost"
- concept_opposition：概念对立或对比，如"nature vs nurture"、"supply and demand"
- proper_noun：专有名词，如特定的理论、模型、机构名称

输出前必须回查：
- 你标注的每个 text 字段，是否能在原句中逐字找到？
- 如果找不到，删除该标注。
""".strip()


def build_term_prompt(deps: TermAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_term_agent() -> Agent[TermAgentDeps, TermDraft]:
    return Agent[TermAgentDeps, TermDraft](
        model=None,
        output_type=TermDraft,
        deps_type=TermAgentDeps,
        instructions=TERM_INSTRUCTIONS,
        name="term_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

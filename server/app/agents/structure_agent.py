"""Structure analysis agent for Academic workflow.

负责标注段落功能和生成全文综合摘要。
帮助用户快速把握论文结构和论证脉络。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.academic_drafts import StructureDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class StructureAgentDeps:
    """Structure agent 依赖。"""

    paragraphs: list[dict[str, object]]
    full_text: str
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


STRUCTURE_INSTRUCTIONS = """
你是一位学术文献结构分析助手。你的任务是阅读英文学术文本，分析段落功能并生成全文综合摘要。

## 段落功能标注

为每个段落标注其在论文结构中的功能。

段落功能类型说明：
- definition：定义段。用于定义关键术语、概念或理论框架。
- background：背景段。介绍研究背景、领域现状或前人工作。
- problem_statement：问题提出段。明确指出研究问题、缺口或挑战。
- methodology：方法段。描述研究方法、实验设计或分析框架。
- evidence：证据段。呈现实验数据、观察结果或支持性证据。
- result：结果段。报告主要发现、实验结果或数据分析结果。
- limitation：限制段。讨论研究的局限性、不足或边界条件。
- transition：过渡段。连接不同部分，引导读者理解论证脉络。
- discussion：讨论段。解释结果意义、与前人工作比较、探讨含义。
- conclusion：结论段。总结主要发现、贡献和未来方向。

段落功能标注要求：
- paragraph_id：段落的唯一标识
- role：段落功能类型
- label：简短的中文标签，如"问题提出"、"方法介绍"
- summary_zh：该段落的内容摘要。用中文概括这个段落的主要内容和在论证中的作用。
- key_claim（可选）：该段落的核心主张或发现。

## 全文综合摘要

为整篇文章生成综合摘要，帮助用户快速把握论文的贡献。

全文摘要要求：
- research_problem_zh（可选）：研究问题。用中文概括本文要解决的核心问题。
- methodology_zh（可选）：研究方法。用中文概括本文采用的主要方法或实验设计。
- key_findings_zh（可选）：核心发现。用中文概括本文的主要实验结果或理论贡献。
- limitations_zh（可选）：研究限制。用中文概括作者明确提到的或隐含的研究局限性。
- overall_significance_zh（可选）：整体意义。用中文概括这项工作在该领域的位置和贡献。

## 输出原则

1. 段落功能标注要准确反映该段落在论证结构中的作用
2. 全文摘要要简洁、准确，突出论文的核心贡献
3. 不要添加原文没有的信息
4. 如果某些字段（如 limitations_zh）在原文中没有明确体现，可以留空

输出前必须回查：
- 你标注的每个 paragraph_id 是否与输入中的段落标识对应？
- 全文摘要中的信息是否都来自原文？
""".strip()


def build_structure_prompt(deps: StructureAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.paragraphs,
    )


@lru_cache(maxsize=1)
def get_structure_agent() -> Agent[StructureAgentDeps, StructureDraft]:
    return Agent[StructureAgentDeps, StructureDraft](
        model=None,
        output_type=StructureDraft,
        deps_type=StructureAgentDeps,
        instructions=STRUCTURE_INSTRUCTIONS,
        name="structure_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

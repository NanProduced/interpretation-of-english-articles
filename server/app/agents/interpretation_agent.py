"""Interpretation agent for Academic workflow.

负责解释"这句话真正想表达什么"，以及"为什么不能只按字面直译理解"。
这是 academic 模式的核心输出之一。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.academic_drafts import InterpretationDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class InterpretationAgentDeps:
    """Interpretation agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


INTERPRETATION_INSTRUCTIONS = """
你是一位学术文献解释性理解助手。你的任务是阅读英文学术文本，找出那些字面翻译可能带来理解偏差的句子或短语，解释作者真正想表达什么。

你的判断标准：
- 标注那些字面翻译可能误导读者的句子或短语
- 优先选择学术写作中常见的委婉表达、间接说法、专业约定
- 简单直白的句子不需要标注

关于锚点：
- spans 中的 text 必须从原句中精确摘取，不要改写
- 如果 spans 为空，表示对整句的解释

输出要求：
- literal_translation（可选）：提供字面翻译，用于对比说明为什么字面翻译会带来理解偏差
- intended_meaning_zh：作者真正想表达的意思。用自然的中文解释这句话的真实意图
- why_not_literal（可选）：为什么不能只按字面理解。解释学术写作中的委婉表达、间接说法、专业约定等
- rhetorical_purpose（可选）：修辞目的。说明作者使用这种表达方式的策略性意图（如谨慎、客观、留有余地等）

学术写作中常见的需要解释的情况：
1. 委婉表达负面结果：
   - "These results should be interpreted with caution" 字面是"谨慎解释"，实际是"结果可能有问题/局限性"
   - "Further research is needed" 字面是"需要更多研究"，实际是"当前研究不够完整/结论不够确定"

2. 间接批评：
   - "Previous work has focused on X" 字面是"之前的工作关注X"，实际可能是"之前的工作忽略了Y"
   - "While X is useful, it has limitations" 字面是"X有用但有局限"，实际是"X不够好，我们的方法更好"

3. 专业约定：
   - "We hypothesize that" 字面是"我们假设"，实际是"这是我们的核心主张/我们相信这是对的"
   - "Our results suggest that" 字面是"结果暗示"，实际是"我们的证据支持这个结论"

4. 谨慎措辞：
   - "may indicate"、"could suggest"、"appears to" 等表达，作者是在保持学术严谨性，不是不确定

输出前必须回查：
- 如果你提供了 spans，每个 span 中的 text 是否能在原句中逐字找到？
- 如果找不到，删除该标注或移除 spans。
""".strip()


def build_interpretation_prompt(deps: InterpretationAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_interpretation_agent() -> Agent[InterpretationAgentDeps, InterpretationDraft]:
    return Agent[InterpretationAgentDeps, InterpretationDraft](
        model=None,
        output_type=InterpretationDraft,
        deps_type=InterpretationAgentDeps,
        instructions=INTERPRETATION_INSTRUCTIONS,
        name="interpretation_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

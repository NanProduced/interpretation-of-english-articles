"""Academic translation agent for Academic workflow.

负责为学术文本生成翻译，风格更偏向学术化。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.academic_drafts import AcademicTranslationDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class AcademicTranslationAgentDeps:
    """Academic translation agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


ACADEMIC_TRANSLATION_INSTRUCTIONS = """
你是一位学术文献翻译助手。你的任务是为英文学术文章的每个句子生成中文翻译，并给出一个中文标题。

翻译要求：
- 每个句子都必须有对应翻译，不要遗漏或合并
- 句间翻译保持连贯，代词指代要一致
- 标题概括全文主旨，使用中文短标题，不带句号，不用 Emoji
- 专有名词或学术术语首次出现时建议用"中文（英文）"格式
- 引用内容照常翻译，不要加"原文引用："之类的前缀

学术翻译风格要求：
- 保持学术严谨性，避免过于口语化的表达
- 专业术语要准确，符合中文学术界的常用译法
- 长句翻译要注意逻辑层次，保持论证的连贯性
- 注意学术写作中的委婉表达和谨慎措辞，翻译时要体现这种语气

例如：
- "These results should be interpreted with caution" 不应直译为"这些结果应该谨慎解释"，而应译为"对这些结果的解读需持谨慎态度"或"这些结果的解释存在一定局限性"
- "Further research is needed" 不应直译为"需要进一步研究"，而应译为"后续研究可进一步探讨"或"本研究的局限性有待未来工作补充"
""".strip()


def build_academic_translation_prompt(deps: AcademicTranslationAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_academic_translation_agent() -> Agent[AcademicTranslationAgentDeps, AcademicTranslationDraft]:
    return Agent[AcademicTranslationAgentDeps, AcademicTranslationDraft](
        model=None,
        output_type=AcademicTranslationDraft,
        deps_type=AcademicTranslationAgentDeps,
        instructions=ACADEMIC_TRANSLATION_INSTRUCTIONS,
        name="academic_translation_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

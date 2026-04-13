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
你是英语阅读结构维度标注器，为英文句子生成 grammar_note 和 sentence_analysis。

核心原则（必须严格遵守）：
1. Schema 约束输出结构，你只决定哪些结构点值得讲。
2. 锚点文本必须精确摘自原句子串，绝不允许改写或拼写错误。
3. 中文字段必须使用自然、流畅的中文，不堆砌晦涩术语。
4. 不确定时不标，不猜，不补背景知识，不输出 schema 之外的内容。
5. 简单句绝不要标 —— 不拆也能直接读懂的句子不需要任何产出。

GrammarNote vs SentenceAnalysis 的严格分工：
- GrammarNote：解决"这里这个结构怎么理解/怎么用"，只讲一个清晰的局部语法点。
- SentenceAnalysis：解决"整句应该怎么拆开读"，用于真正影响理解的复杂句，必须同时输出 2-6 个 chunks。
- 绝不要用 GrammarNote 拆解整个复杂句的主谓宾结构。

硬性禁止项：
- 绝不要在 note_zh / analysis_zh 里输出 markdown 格式，也不要包含 "示例" / "如：" 等内容。
- 如果句子本身只是一般并列、简单被动或普通时间状语，绝不要强行标注。
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
        output_retries=2,
        instrument=False,
    )

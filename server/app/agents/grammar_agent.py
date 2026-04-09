"""Grammar agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import GrammarDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_composer import build_agent_prompt
from app.services.analysis.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class GrammarAgentDeps:
    """Grammar agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


GRAMMAR_INSTRUCTIONS = """
你是英语阅读结构维度标注器，为英文句子生成 grammar_note 和 sentence_analysis。

核心原则：
1. Schema 约束输出结构，你只决定哪些结构点值得讲。
2. 锚点文本必须直接摘自原句，不改写。
3. 中文字段写自然中文，不堆术语。
4. 不确定时不标，不猜，不补背景知识，不输出 schema 之外的内容。
5. 简单句不标 —— 不拆也能直接读懂的句子不需要产出。

GrammarNote vs SentenceAnalysis 的分工：
- GrammarNote：解决"这里这个结构怎么理解/怎么用"，只讲一个清晰的局部语法点。
- SentenceAnalysis：解决"整句应该怎么拆开读"，用于真正影响理解的复杂句，需给出 chunks。
- 如果一个复杂句值得完整拆解，优先给 1 个高质量 SentenceAnalysis，而非拆成多个低价值 GrammarNote。

触发与克制：
GrammarNote 触发：倒装 | 从句功能 | 非谓语 | 固定句型 | 易混辨析 | 强调/省略/插入
GrammarNote 不标：简单时间状语 | 普通并列 | 简单被动
SentenceAnalysis 触发：嵌套从句 | 压缩结构(如 result in...being done) | 插入打断主干 | 并列+从句叠加
SentenceAnalysis 不标：不拆也能直接读懂的句子

写作要求：
1. note_zh 控制在 1-3 句，先说"怎么理解"再说"为什么"。
2. analysis_zh 控制在 2-4 句，先讲主干再讲阅读顺序。
3. SentenceAnalysis 必须同时输出 2-6 个 chunks，覆盖主干和关键层次，text 为原句真实子串。
4. 不要在 note_zh / analysis_zh 里输出 markdown 格式；结构化展示由后端统一包装。

【示例 1：GrammarNote · 倒装】
句子："Not only did the policy raise costs, but it also reduced supply."
输出：
- type: grammar_note
- spans: [{"text":"Not only"},{"text":"did"},{"text":"but"}]
- label: not only...but also 倒装结构
- note_zh: Not only 放在句首时，前半句触发部分倒装，所以先看到 did 再看到主语和谓语。阅读时先理解前半句倒装主干，再把 but 后面的补充接上。

【示例 2：SentenceAnalysis · 压缩结构】
句子："Higher gas prices result in farmers being forced to pay more for fertilizer."
输出：
- type: sentence_analysis
- label: 主句加 result in 压缩结构
- analysis_zh: 先抓主句 Higher gas prices result in，意思是"更高的油价导致……"。后面的 farmers being forced to pay more 是 result in 承接的结果，整体理解为"农民被迫支付更多化肥成本"。不要把 being forced 单独拆掉，它和 to pay more 连在一起才完整。
- chunks: [{"order":1,"label":"主干触发","text":"Higher gas prices result in"},{"order":2,"label":"结果内容","text":"farmers being forced to pay more for fertilizer"}]

【示例 3：不标】
句子："He gets up at six and goes to school by bus."
→ 不产出，结构简单直接。

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

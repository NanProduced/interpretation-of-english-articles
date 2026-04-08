"""Grammar agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import GrammarDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_strategy import PromptStrategy


@dataclass
class GrammarAgentDeps:
    """Grammar agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


GRAMMAR_INSTRUCTIONS = """
你是一名英语阅读分析标注器，专注结构维度标注。

任务：为英文句子生成 grammar_note、sentence_analysis 标注。

【核心原则】
1. schema 已经约束输出结构；你只需要决定哪些结构点真正值得讲。
2. 所有锚点文本都必须直接摘自对应句子，不能改写。
3. 所有中文字字段都要写自然中文。
4. 不确定时不标，不猜；不补背景知识，不输出 schema 之外的内容。
5. baseline 追求复杂句优先、简单句从严，不追求“每篇都要有很多句解”。

【组件边界】
1. GrammarNote 只讲一个清晰的局部语法点；多段锚点只在确实需要时使用。
2. SentenceAnalysis 用于真正影响理解的复杂句，应说明主干、层次关系和理解顺序。
3. 如果一个复杂句值得完整拆解，优先给 1 个高质量 SentenceAnalysis，而不是拆成多个低价值 GrammarNote。

【写作要求】
1. note_zh 和 analysis_zh 都要写成适合前端卡片展示的简洁说明，不要堆成长段散文。
2. 先写“怎么理解这句/这个结构”，再补“为什么”，避免只堆术语定义。
3. GrammarNote 的 note_zh 控制在 1 到 3 句内，直接解释该结构在当前句子里的作用。
4. SentenceAnalysis 的 analysis_zh 控制在 2 到 4 句内，先讲整句主干，再讲阅读顺序或难点。
5. 不要在 note_zh / analysis_zh 里自行输出 markdown 标题、列表或表格；结构化展示由后端 projection 统一包装。

【SentenceAnalysis 强触发条件】
1. what/how/that/which 等引导的嵌套从句。
2. result in ... being done 这类压缩结构或复杂补足语。
3. 插入语、同位语或修饰成分打断主谓主干。
4. 并列结构和从句嵌套同时存在。

【克制规则】
1. 简单陈述句、简单并列谓语、常见时间状语短语默认不出 sentence_entry。
2. 不要把介词短语作时间状语、普通并列动作、简单被动语态机械地做成 GrammarNote。
3. 如果一句话不拆也能直接读懂，就不要为了“有产出”而硬标。

【Few-shot 示例 1：GrammarNote】
句子："Not only did the policy raise costs, but it also reduced supply."
输出：
- type: grammar_note, sentence_id: s1, spans: [{"text":"Not only","role":"trigger"},{"text":"did","role":"aux"},{"text":"but","role":"conjunction"}], label: not only...but... 倒装, note_zh: Not only 放在句首时，前半句会触发部分倒装，所以这里用了 did the policy raise costs。but 后面补充并列结果，整句可以按“前半句倒装 + 后半句补充”来理解。

【Few-shot 示例 2：SentenceAnalysis】
句子："Higher gas prices result in farmers being forced to pay more for fertilizer."
输出：
- type: sentence_analysis, sentence_id: s1, label: 主句加 result in 压缩结构, analysis_zh: 先抓主句 Higher gas prices result in，意思是“更高的油价导致……”。后面的 farmers being forced to pay more for fertilizer 是 result in 后面承接的结果内容，可以整体理解为“农民被迫支付更多化肥成本”。阅读时不要把 being forced 单独拆掉，它和后面的 to pay more 连在一起才完整。

【Few-shot 示例 3：不要标】
句子："He gets up at six and goes to school by bus."
输出：
- 这句可以不做 grammar_note 或 sentence_analysis，因为结构简单直接。

【输出前自检】
1. 每个 annotation 都必须真正帮助读懂文章，而不是为了凑数量。
2. 所有锚点文本必须能在对应句子里直接找到。
3. 如果一句复杂句已经有高质量 SentenceAnalysis，先检查是否还需要额外 GrammarNote；大多数情况下不需要。
""".strip()


def _render_strategy(strategy: PromptStrategy) -> list[str]:
    lines = [
        f"- reading_goal: {strategy.reading_goal}",
        f"- reading_variant: {strategy.reading_variant}",
    ]
    if strategy.annotation_style:
        lines.append(f"- annotation_style: {strategy.annotation_style}")
    if strategy.grammar_granularity:
        lines.append(f"- grammar_granularity: {strategy.grammar_granularity}")
    if strategy.grammar_granularity == "focused":
        lines.append("- 执行方式: 只标最影响理解的语法点，数量从严。")
    elif strategy.grammar_granularity == "balanced":
        lines.append("- 执行方式: 平衡覆盖，但复杂句优先，简单句默认不标。")
    elif strategy.grammar_granularity == "structural":
        lines.append("- 执行方式: 更关注句子层次与结构关系，适度提高 SentenceAnalysis 比重。")
    return lines


def _render_examples(examples: list[ExampleEntry]) -> list[str]:
    if not examples:
        return []
    lines = ["补充示例："]
    for idx, example in enumerate(examples, start=1):
        lines.extend(
            [
                f"{idx}. [{example.example_type}] {example.sentence_text}",
                example.output_fragment,
            ]
        )
    return lines


def build_grammar_prompt(deps: GrammarAgentDeps) -> str:
    sentence_lines = [
        f"{sentence['sentence_id']}: {sentence['text']}"
        for sentence in deps.sentences
    ]
    return "\n".join(
        [
            "策略：",
            *_render_strategy(deps.prompt_strategy),
            *(_render_examples(deps.examples)),
            "句子列表：",
            *sentence_lines,
        ]
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

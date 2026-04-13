"""Example strategy for V3 workflow.

负责 example selection。
设计原则：
- baseline = 最少 few-shot
- 后续可通过 RAG 注入 dynamic few-shot
- 不影响 baseline 稳定性
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.internal.execution_plan import GoalExecutionPlan


@dataclass
class ExampleEntry:
    """Example 条目。"""
    example_type: Literal["vocab", "phrase", "context", "grammar", "sentence_analysis", "translation"]
    sentence_text: str
    output_fragment: str


@dataclass
class ExampleStrategy:
    """Example 策略。"""
    examples: list[ExampleEntry]
    selection_mode: Literal["baseline", "rag", "manual"] = "baseline"


# V3 baseline: 无额外 few-shot（agent 内联 few-shot 已足够）
# 文档说明：baseline 可以是空 examples 或极少 examples
BASELINE_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="phrase",
        sentence_text="The documentary scored 100 per cent on Rotten Tomatoes.",
        output_fragment='{"type": "phrase_gloss", "text": "scored 100 per cent", "phrase_type": "collocation", "zh": "获得百分之百的评分"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The visuals rendered the ancient world far more vivid than earlier documentaries.",
        output_fragment='{"type": "context_gloss", "text": "rendered", "gloss": "把...呈现出来", "reason": "词典基本义不足以解释这里的视觉渲染含义"}',
    ),
    ExampleEntry(
        example_type="vocab",
        sentence_text="This dexterous use of tactile feedback helps refugees.",
        output_fragment='{"type": "vocab_highlight", "text": "dexterous"}',
    )
]

BASELINE_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="Not only did the policy raise costs, but it also reduced supply.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "Not only"}, {"text": "did"}, {"text": "but"}], "label": "not only...but also 倒装结构", "note_zh": "Not only 放在句首时触发部分倒装，所以先看到 did 再看到主语。阅读时先理解前半句主干，再接上 but 后面的补充。"}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="Higher gas prices result in farmers being forced to pay more for fertilizer.",
        output_fragment='{"type": "sentence_analysis", "label": "主干与 result in 结果结构", "analysis_zh": "先抓主干 Higher gas prices result in (更高的油价导致)。后面 farmers being forced... 是导致的结果，整体理解为农民被迫支付更多。不要把 being forced 拆开，它和 to pay more 是一个连贯动作。", "chunks": [{"order": 1, "label": "主干触发", "text": "Higher gas prices result in"}, {"order": 2, "label": "结果内容", "text": "farmers being forced to pay more for fertilizer"}]}',
    )
]

BASELINE_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The visuals rendered the ancient world far more vivid than earlier documentaries.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "这些画面把远古世界呈现得比以往的纪录片生动得多。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="The documentary scored 100 per cent on Rotten Tomatoes, making it the highest-rated nature film.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "这部纪录片在烂番茄（Rotten Tomatoes）上获得了百分之百的好评，成为评分最高的自然类影片。"}',
    )
]


def get_vocabulary_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 vocabulary agent 的 example 策略。"""
    examples = BASELINE_VOCABULARY_EXAMPLES if plan.few_shot_mode == "baseline" else []
    return ExampleStrategy(
        examples=examples,
        selection_mode=plan.few_shot_mode,
    )


def get_grammar_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 grammar agent 的 example 策略。"""
    examples = BASELINE_GRAMMAR_EXAMPLES if plan.few_shot_mode == "baseline" else []
    return ExampleStrategy(
        examples=examples,
        selection_mode=plan.few_shot_mode,
    )


def get_translation_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 translation agent 的 example 策略。"""
    examples = BASELINE_TRANSLATION_EXAMPLES if plan.few_shot_mode == "baseline" else []
    return ExampleStrategy(
        examples=examples,
        selection_mode=plan.few_shot_mode,
    )

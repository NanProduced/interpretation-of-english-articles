"""Example strategy for V3 workflow.

负责 example selection。
设计原则：
- baseline = 最少 few-shot
- 后续可通过 RAG 注入 dynamic few-shot
- 不影响 baseline 稳定性
- 示例要体现 variant 的差异化方向
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.prompting.prompt_loader import load_examples


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


def _load_baseline_examples(example_name: str, variant: str) -> list[ExampleEntry]:
    raw_entries = load_examples(example_name, variant)
    return [
        ExampleEntry(
            example_type=entry["example_type"],
            sentence_text=entry["sentence_text"],
            output_fragment=entry["output_fragment"],
        )
        for entry in raw_entries
    ]


def _resolve_rag_examples(
    example_name: str,
    variant: str,
    sentences: list[dict] | None = None,
) -> list[ExampleEntry]:
    if sentences is None:
        return []
    # TODO: 接入 grammar_rag_service，按 grammar-rag-design.md 实现
    # 当前返回空列表，RAG 未上线时自动回退到 baseline
    return []


def get_vocabulary_example_strategy(
    plan: GoalExecutionPlan,
    sentences: list[dict] | None = None,
) -> ExampleStrategy:
    """获取 vocabulary agent 的 example 策略。"""
    if plan.few_shot_mode == "rag":
        rag_examples = _resolve_rag_examples("vocabulary", plan.variant_id, sentences)
        if rag_examples:
            return ExampleStrategy(examples=rag_examples, selection_mode="rag")
        return ExampleStrategy(
            examples=_load_baseline_examples("vocabulary", plan.variant_id),
            selection_mode="rag_fallback",
        )
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)

    return ExampleStrategy(
        examples=_load_baseline_examples("vocabulary", plan.variant_id),
        selection_mode="baseline",
    )


def get_grammar_example_strategy(
    plan: GoalExecutionPlan,
    sentences: list[dict] | None = None,
) -> ExampleStrategy:
    """获取 grammar agent 的 example 策略。"""
    if plan.few_shot_mode == "rag":
        rag_examples = _resolve_rag_examples("grammar", plan.variant_id, sentences)
        if rag_examples:
            return ExampleStrategy(examples=rag_examples, selection_mode="rag")
        return ExampleStrategy(
            examples=_load_baseline_examples("grammar", plan.variant_id),
            selection_mode="rag_fallback",
        )
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)

    return ExampleStrategy(
        examples=_load_baseline_examples("grammar", plan.variant_id),
        selection_mode="baseline",
    )


def get_translation_example_strategy(
    plan: GoalExecutionPlan,
    sentences: list[dict] | None = None,
) -> ExampleStrategy:
    """获取 translation agent 的 example 策略。"""
    if plan.few_shot_mode == "rag":
        rag_examples = _resolve_rag_examples("translation", plan.variant_id, sentences)
        if rag_examples:
            return ExampleStrategy(examples=rag_examples, selection_mode="rag")
        return ExampleStrategy(
            examples=_load_baseline_examples("translation", plan.variant_id),
            selection_mode="rag_fallback",
        )
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)

    return ExampleStrategy(
        examples=_load_baseline_examples("translation", plan.variant_id),
        selection_mode="baseline",
    )

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

from app.schemas.internal.analysis import UserRules


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
BASELINE_VOCABULARY_EXAMPLES: list[ExampleEntry] = []
BASELINE_GRAMMAR_EXAMPLES: list[ExampleEntry] = []
BASELINE_TRANSLATION_EXAMPLES: list[ExampleEntry] = []


def get_vocabulary_example_strategy(
    user_rules: UserRules,
) -> ExampleStrategy:
    """获取 vocabulary agent 的 example 策略。

    当前返回空策略（baseline）。
    后续可通过 RAG 注入 dynamic few-shot。
    """
    return ExampleStrategy(
        examples=BASELINE_VOCABULARY_EXAMPLES,
        selection_mode="baseline",
    )


def get_grammar_example_strategy(
    user_rules: UserRules,
) -> ExampleStrategy:
    """获取 grammar agent 的 example 策略。

    当前返回空策略（baseline）。
    后续可通过 RAG 注入 dynamic few-shot。
    """
    return ExampleStrategy(
        examples=BASELINE_GRAMMAR_EXAMPLES,
        selection_mode="baseline",
    )


def get_translation_example_strategy(
    user_rules: UserRules,
) -> ExampleStrategy:
    """获取 translation agent 的 example 策略。

    当前返回空策略（baseline）。
    后续可通过 RAG 注入 dynamic few-shot。
    """
    return ExampleStrategy(
        examples=BASELINE_TRANSLATION_EXAMPLES,
        selection_mode="baseline",
    )

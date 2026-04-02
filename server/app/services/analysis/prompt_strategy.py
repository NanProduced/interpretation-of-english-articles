"""Prompt strategy for V3 workflow.

负责为各 agent 构建 prompt 和 strategy bundle。
设计原则：
- node 不直接拼凑零散 prompt 片段
- agent 通过统一的 strategy builder 获取 prompt 和 examples
- 不同 agent 可以接收不同的 strategy 子集
- baseline 配置尽量短，尽量少 few-shot
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.internal.analysis import UserRules


@dataclass
class PromptStrategy:
    """Prompt 策略。"""
    reading_goal: str
    reading_variant: str
    annotation_style: str | None = None
    translation_style: str | None = None
    grammar_granularity: str | None = None
    vocabulary_policy: str | None = None
    extra_instructions: str | None = None


def build_vocabulary_prompt_strategy(
    user_rules: UserRules,
) -> PromptStrategy:
    """构建 vocabulary agent 的 prompt 策略。

    基线配置：
    - 不额外叠加复杂提示
    - 不额外叠加大量 few-shot
    """
    return PromptStrategy(
        reading_goal=user_rules.reading_goal,
        reading_variant=user_rules.reading_variant,
        vocabulary_policy=user_rules.vocabulary_policy,
        annotation_style=user_rules.annotation_style,
    )


def build_grammar_prompt_strategy(
    user_rules: UserRules,
) -> PromptStrategy:
    """构建 grammar agent 的 prompt 策略。

    基线配置：
    - 不额外叠加复杂提示
    - 保持 grammar_granularity 控制
    """
    return PromptStrategy(
        reading_goal=user_rules.reading_goal,
        reading_variant=user_rules.reading_variant,
        grammar_granularity=user_rules.grammar_granularity,
        annotation_style=user_rules.annotation_style,
    )


def build_translation_prompt_strategy(
    user_rules: UserRules,
) -> PromptStrategy:
    """构建 translation agent 的 prompt 策略。

    基线配置：
    - 不额外叠加复杂提示
    - 保持 translation_style 控制
    """
    return PromptStrategy(
        reading_goal=user_rules.reading_goal,
        reading_variant=user_rules.reading_variant,
        translation_style=user_rules.translation_style,
    )


def build_repair_prompt_strategy(
    error_context: str,
) -> PromptStrategy:
    """构建 repair agent 的 prompt 策略。

    注入错误上下文。
    """
    return PromptStrategy(
        reading_goal="repair",
        reading_variant="repair",
        extra_instructions=error_context,
    )

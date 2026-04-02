"""Strategy bundle builder for V3 workflow.

统一的 strategy bundle 构建器。
设计原则：
- 为所有 agent 提供同一套配置来源
- 策略层解耦，不写死在 node 内
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.internal.analysis import UserRules
from app.services.analysis.example_strategy import (
    ExampleStrategy,
    get_grammar_example_strategy,
    get_translation_example_strategy,
    get_vocabulary_example_strategy,
)
from app.services.analysis.prompt_strategy import (
    PromptStrategy,
    build_grammar_prompt_strategy,
    build_translation_prompt_strategy,
    build_vocabulary_prompt_strategy,
)


@dataclass
class StrategyBundle:
    """策略Bundle，包含 prompt 和 example 策略。"""
    prompt_strategy: PromptStrategy
    example_strategy: ExampleStrategy


def build_vocabulary_bundle(
    user_rules: UserRules,
) -> StrategyBundle:
    """构建 vocabulary agent 的 strategy bundle。"""
    return StrategyBundle(
        prompt_strategy=build_vocabulary_prompt_strategy(user_rules),
        example_strategy=get_vocabulary_example_strategy(user_rules),
    )


def build_grammar_bundle(
    user_rules: UserRules,
) -> StrategyBundle:
    """构建 grammar agent 的 strategy bundle。"""
    return StrategyBundle(
        prompt_strategy=build_grammar_prompt_strategy(user_rules),
        example_strategy=get_grammar_example_strategy(user_rules),
    )


def build_translation_bundle(
    user_rules: UserRules,
) -> StrategyBundle:
    """构建 translation agent 的 strategy bundle。"""
    return StrategyBundle(
        prompt_strategy=build_translation_prompt_strategy(user_rules),
        example_strategy=get_translation_example_strategy(user_rules),
    )

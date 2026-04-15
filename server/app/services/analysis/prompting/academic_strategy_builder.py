"""Strategy bundle builder for Academic workflow.

为 academic agents 提供统一的 strategy bundle 构建器。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.prompting.example_strategy import (
    ExampleStrategy,
    get_grammar_example_strategy,
    get_translation_example_strategy,
    get_vocabulary_example_strategy,
)
from app.services.analysis.prompting.prompt_strategy import (
    PromptStrategy,
    build_grammar_prompt_strategy,
    build_translation_prompt_strategy,
    build_vocabulary_prompt_strategy,
)


@dataclass
class AcademicStrategyBundle:
    """Academic 模式的策略 Bundle，包含 prompt 和 example 策略。"""
    prompt_strategy: PromptStrategy
    example_strategy: ExampleStrategy


def build_term_bundle(plan: GoalExecutionPlan) -> AcademicStrategyBundle:
    """构建 term agent 的 strategy bundle。

    复用 vocabulary 的 prompt 策略，但调整为学术术语导向。
    """
    return AcademicStrategyBundle(
        prompt_strategy=build_vocabulary_prompt_strategy(plan),
        example_strategy=get_vocabulary_example_strategy(plan),
    )


def build_logic_bundle(plan: GoalExecutionPlan) -> AcademicStrategyBundle:
    """构建 logic agent 的 strategy bundle。

    复用 grammar 的 prompt 策略，但调整为逻辑关系导向。
    """
    return AcademicStrategyBundle(
        prompt_strategy=build_grammar_prompt_strategy(plan),
        example_strategy=get_grammar_example_strategy(plan),
    )


def build_interpretation_bundle(plan: GoalExecutionPlan) -> AcademicStrategyBundle:
    """构建 interpretation agent 的 strategy bundle。

    复用 translation 的 prompt 策略，但调整为解释性理解导向。
    """
    return AcademicStrategyBundle(
        prompt_strategy=build_translation_prompt_strategy(plan),
        example_strategy=get_translation_example_strategy(plan),
    )


def build_structure_bundle(plan: GoalExecutionPlan) -> AcademicStrategyBundle:
    """构建 structure agent 的 strategy bundle。

    复用 grammar 的 prompt 策略，但调整为结构分析导向。
    """
    return AcademicStrategyBundle(
        prompt_strategy=build_grammar_prompt_strategy(plan),
        example_strategy=get_grammar_example_strategy(plan),
    )


def build_academic_translation_bundle(plan: GoalExecutionPlan) -> AcademicStrategyBundle:
    """构建 academic translation agent 的 strategy bundle。

    复用 translation 的 prompt 策略。
    """
    return AcademicStrategyBundle(
        prompt_strategy=build_translation_prompt_strategy(plan),
        example_strategy=get_translation_example_strategy(plan),
    )

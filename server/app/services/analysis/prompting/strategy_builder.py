"""Strategy bundle builder for V3 workflow.

统一的 strategy bundle 构建器。
设计原则：
- 为所有 agent 提供同一套配置来源
- 策略层解耦，不写死在 node 内
- 只使用新的声明式 prompt profile 体系（不再保留旧路径）
- 新体系的行为与旧实现完全一致（通过迁移内置 profiles 保证）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.prompting.example_strategy import (
    ExampleStrategy,
)
from app.services.analysis.prompting.profiles import (
    ProfileResolver,
    init_profiles,
)
from app.services.analysis.prompting.prompt_strategy import (
    PromptStrategy,
)


@dataclass
class StrategyBundle:
    """策略Bundle，包含 prompt 和 example 策略。"""
    prompt_strategy: PromptStrategy
    example_strategy: ExampleStrategy


def _get_resolver() -> ProfileResolver:
    """获取解析器，确保内置 profiles 已注册。"""
    init_profiles()
    return ProfileResolver()


def build_vocabulary_bundle(
    plan: GoalExecutionPlan,
    *,
    profile_version: str | None = None,
) -> StrategyBundle:
    """构建 vocabulary agent 的 strategy bundle。

    Args:
        plan: 执行计划
        profile_version: 可选的 profile 版本号，用于支持版本化的 prompt 配置。
            如果未提供，使用默认版本。
    """
    resolver = _get_resolver()
    return resolver.get_strategy_bundle(plan, "vocabulary", profile_version)


def build_grammar_bundle(
    plan: GoalExecutionPlan,
    *,
    profile_version: str | None = None,
) -> StrategyBundle:
    """构建 grammar agent 的 strategy bundle。

    Args:
        plan: 执行计划
        profile_version: 可选的 profile 版本号，用于支持版本化的 prompt 配置。
            如果未提供，使用默认版本。
    """
    resolver = _get_resolver()
    return resolver.get_strategy_bundle(plan, "grammar", profile_version)


def build_translation_bundle(
    plan: GoalExecutionPlan,
    *,
    profile_version: str | None = None,
) -> StrategyBundle:
    """构建 translation agent 的 strategy bundle。

    Args:
        plan: 执行计划
        profile_version: 可选的 profile 版本号，用于支持版本化的 prompt 配置。
            如果未提供，使用默认版本。
    """
    resolver = _get_resolver()
    return resolver.get_strategy_bundle(plan, "translation", profile_version)


def build_term_bundle(
    plan: GoalExecutionPlan,
    *,
    profile_version: str | None = None,
) -> StrategyBundle:
    """构建 term agent 的 strategy bundle（academic workflow）。

    Args:
        plan: 执行计划
        profile_version: 可选的 profile 版本号
    """
    resolver = _get_resolver()
    return resolver.get_strategy_bundle(plan, "term", profile_version)


def build_academic_translation_bundle(
    plan: GoalExecutionPlan,
    *,
    profile_version: str | None = None,
) -> StrategyBundle:
    """构建 academic_translation agent 的 strategy bundle（academic workflow）。

    Args:
        plan: 执行计划
        profile_version: 可选的 profile 版本号
    """
    resolver = _get_resolver()
    return resolver.get_strategy_bundle(plan, "academic_translation", profile_version)


def build_understanding_bundle(
    plan: GoalExecutionPlan,
    *,
    profile_version: str | None = None,
) -> StrategyBundle:
    """构建 understanding agent 的 strategy bundle（academic workflow）。

    Args:
        plan: 执行计划
        profile_version: 可选的 profile 版本号
    """
    resolver = _get_resolver()
    return resolver.get_strategy_bundle(plan, "understanding", profile_version)


def build_strategy_bundle(
    plan: GoalExecutionPlan,
    agent_type: Literal["vocabulary", "grammar", "translation", "term", "academic_translation", "understanding"],
    *,
    profile_version: str | None = None,
) -> StrategyBundle:
    """通用的 strategy bundle 构建函数。

    根据 agent_type 自动选择对应的构建函数。

    Args:
        plan: 执行计划
        agent_type: agent 类型
        profile_version: 可选的 profile 版本号

    Returns:
        StrategyBundle 实例
    """
    if agent_type == "vocabulary":
        return build_vocabulary_bundle(plan, profile_version=profile_version)
    elif agent_type == "grammar":
        return build_grammar_bundle(plan, profile_version=profile_version)
    elif agent_type == "translation":
        return build_translation_bundle(plan, profile_version=profile_version)
    elif agent_type == "term":
        return build_term_bundle(plan, profile_version=profile_version)
    elif agent_type == "academic_translation":
        return build_academic_translation_bundle(plan, profile_version=profile_version)
    elif agent_type == "understanding":
        return build_understanding_bundle(plan, profile_version=profile_version)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

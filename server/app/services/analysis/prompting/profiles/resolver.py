"""Profile 解析器。

根据执行计划解析出对应的 prompt profile。

设计原则：
- 统一使用新的 profile/registry 机制
- 移除所有 legacy fallback 路径
- 如果找不到 profile，抛出明确的错误
"""

from __future__ import annotations

from typing import Literal

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.prompting.example_strategy import ExampleStrategy
from app.services.analysis.prompting.prompt_strategy import PromptStrategy
from app.services.analysis.prompting.profiles.models import PromptProfile
from app.services.analysis.prompting.profiles.registry import ProfileRegistry, get_default_registry


class ProfileResolver:
    """Profile 解析器。

    负责根据执行计划解析出对应的 prompt profile。
    所有配置都来自注册中心，不再有 legacy fallback 路径。
    """

    def __init__(self, registry: ProfileRegistry | None = None) -> None:
        self._registry = registry or get_default_registry()

    def resolve(
        self,
        plan: GoalExecutionPlan,
        version: str | None = None,
    ) -> PromptProfile:
        """根据执行计划解析出对应的 prompt profile。

        解析策略：
        1. 使用 plan.prompt_profile 作为 profile_id 从注册中心查询
        2. 如果指定了 version，使用该版本；否则使用默认版本
        3. 如果注册中心中没有找到，抛出 ValueError

        Args:
            plan: 执行计划
            version: 可选的版本号

        Returns:
            匹配的 PromptProfile

        Raises:
            ValueError: 如果找不到匹配的 profile
        """
        profile_id = plan.prompt_profile
        profile = self._registry.get(profile_id, version)

        if profile is None:
            if version is None:
                raise ValueError(
                    f"Profile '{profile_id}' not found in registry. "
                    f"Ensure init_profiles() has been called."
                )
            else:
                raise ValueError(
                    f"Profile '{profile_id}' version '{version}' not found in registry. "
                    f"Available versions: {[v.to_string() for v in self._registry.list_versions(profile_id)] if self._registry.has_profile(profile_id) else 'none'}"
                )

        return profile

    def get_strategy_bundle(
        self,
        plan: GoalExecutionPlan,
        agent_type: Literal["vocabulary", "grammar", "translation", "term", "academic_translation", "understanding"],
        version: str | None = None,
    ) -> StrategyBundle:
        """获取指定 agent 的策略 bundle。

        Args:
            plan: 执行计划
            agent_type: agent 类型
            version: 可选的版本号

        Returns:
            StrategyBundle 实例

        Raises:
            ValueError: 如果找不到匹配的 profile 或未知的 agent_type
        """
        profile = self.resolve(plan, version)

        if agent_type == "vocabulary":
            prompt_strategy = PromptStrategy(
                profile_id=profile.profile_id,
                reading_goal=profile.reading_goal or plan.goal_id,
                reading_variant=profile.reading_variant or plan.variant_id,
                vocabulary_policy=plan.policy.vocabulary_focus,
                policy_lines=profile.policy_config.vocabulary,
            )
            example_strategy = ExampleStrategy(
                examples=list(profile.example_config.vocabulary),
                selection_mode=profile.example_config.selection_mode,
            )
        elif agent_type == "grammar":
            prompt_strategy = PromptStrategy(
                profile_id=profile.profile_id,
                reading_goal=profile.reading_goal or plan.goal_id,
                reading_variant=profile.reading_variant or plan.variant_id,
                grammar_granularity=plan.policy.grammar_focus,
                policy_lines=profile.policy_config.grammar,
            )
            example_strategy = ExampleStrategy(
                examples=list(profile.example_config.grammar),
                selection_mode=profile.example_config.selection_mode,
            )
        elif agent_type == "translation":
            prompt_strategy = PromptStrategy(
                profile_id=profile.profile_id,
                reading_goal=profile.reading_goal or plan.goal_id,
                reading_variant=profile.reading_variant or plan.variant_id,
                translation_style=plan.policy.translation_focus,
                policy_lines=profile.policy_config.translation,
            )
            example_strategy = ExampleStrategy(
                examples=list(profile.example_config.translation),
                selection_mode=profile.example_config.selection_mode,
            )
        elif agent_type == "term":
            prompt_strategy = PromptStrategy(
                profile_id=profile.profile_id,
                reading_goal=profile.reading_goal or plan.goal_id,
                reading_variant=profile.reading_variant or plan.variant_id,
                vocabulary_policy=plan.policy.vocabulary_focus,
                annotation_style="structural_and_academic",
                policy_lines=profile.policy_config.term,
            )
            example_strategy = ExampleStrategy(
                examples=list(profile.example_config.term),
                selection_mode=profile.example_config.selection_mode,
            )
        elif agent_type == "academic_translation":
            prompt_strategy = PromptStrategy(
                profile_id=profile.profile_id,
                reading_goal=profile.reading_goal or plan.goal_id,
                reading_variant=profile.reading_variant or plan.variant_id,
                translation_style="academic",
                policy_lines=profile.policy_config.academic_translation,
            )
            example_strategy = ExampleStrategy(
                examples=list(profile.example_config.academic_translation),
                selection_mode=profile.example_config.selection_mode,
            )
        elif agent_type == "understanding":
            prompt_strategy = PromptStrategy(
                profile_id=profile.profile_id,
                reading_goal=profile.reading_goal or plan.goal_id,
                reading_variant=profile.reading_variant or plan.variant_id,
                annotation_style="structural_and_academic",
                policy_lines=profile.policy_config.understanding,
            )
            example_strategy = ExampleStrategy(
                examples=list(profile.example_config.understanding),
                selection_mode=profile.example_config.selection_mode,
            )
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        from app.services.analysis.prompting.strategy_builder import StrategyBundle

        return StrategyBundle(
            prompt_strategy=prompt_strategy,
            example_strategy=example_strategy,
        )


_default_resolver: ProfileResolver | None = None


def get_default_resolver() -> ProfileResolver:
    """获取默认的全局解析器实例。"""
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = ProfileResolver()
    return _default_resolver


def resolve_profile(
    plan: GoalExecutionPlan,
    version: str | None = None,
) -> PromptProfile:
    """使用默认解析器解析 profile。

    Args:
        plan: 执行计划
        version: 可选的版本号

    Returns:
        匹配的 PromptProfile

    Raises:
        ValueError: 如果找不到匹配的 profile
    """
    return get_default_resolver().resolve(plan, version)

"""Profile 解析器。

根据执行计划解析出对应的 prompt profile，保持与现有逻辑的兼容性。
"""

from __future__ import annotations

from typing import Literal

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.prompting.example_strategy import (
    INTERMEDIATE_GRAMMAR_EXAMPLES,
    INTERMEDIATE_TRANSLATION_EXAMPLES,
    INTERMEDIATE_VOCABULARY_EXAMPLES,
    ExampleEntry,
    ExampleStrategy,
)
from app.services.analysis.prompting.prompt_strategy import (
    PromptStrategy,
    build_grammar_prompt_strategy,
    build_translation_prompt_strategy,
    build_vocabulary_prompt_strategy,
)
from app.services.analysis.prompting.profiles.models import (
    ExampleConfig,
    PromptPolicyConfig,
    PromptProfile,
)
from app.services.analysis.prompting.profiles.registry import (
    ProfileRegistry,
    get_default_registry,
)


class ProfileResolver:
    """Profile 解析器。

    负责根据执行计划解析出对应的 prompt profile，支持：
    1. 从注册中心查询已注册的 profile
    2. 回退到旧的实现逻辑（保持兼容性）
    3. 支持版本化查询

    设计原则：
    - 优先使用新的注册中心机制
    - 如果注册中心中没有找到匹配的 profile，回退到旧的实现
    - 保持与现有执行计划的完全兼容性
    """

    def __init__(self, registry: ProfileRegistry | None = None) -> None:
        self._registry = registry or get_default_registry()

    def resolve(
        self,
        plan: GoalExecutionPlan,
        version: str | None = None,
    ) -> PromptProfile | None:
        """根据执行计划解析出对应的 prompt profile。

        解析策略：
        1. 首先尝试使用 plan.prompt_profile 作为 profile_id 从注册中心查询
        2. 如果指定了 version，使用该版本；否则使用默认版本
        3. 如果注册中心中没有找到，返回 None（调用者可以选择回退到旧逻辑）

        Args:
            plan: 执行计划
            version: 可选的版本号

        Returns:
            匹配的 PromptProfile，若无则返回 None
        """
        profile_id = plan.prompt_profile
        return self._registry.get(profile_id, version)

    def resolve_or_fallback(
        self,
        plan: GoalExecutionPlan,
        version: str | None = None,
    ) -> ProfileResolutionResult:
        """解析 profile，如果找不到则回退到旧的实现。

        这个方法保证返回一个结果，无论注册中心中是否有匹配的 profile。

        Args:
            plan: 执行计划
            version: 可选的版本号

        Returns:
            ProfileResolutionResult，包含解析结果和来源标识
        """
        profile = self.resolve(plan, version)

        if profile is not None:
            return ProfileResolutionResult(
                profile=profile,
                source=ResolutionSource.REGISTRY,
                plan=plan,
            )

        return ProfileResolutionResult(
            profile=self._build_fallback_profile(plan),
            source=ResolutionSource.LEGACY,
            plan=plan,
        )

    def _build_fallback_profile(self, plan: GoalExecutionPlan) -> PromptProfile:
        """构建回退的 profile（使用旧的实现逻辑）。

        这个方法确保即使注册中心中没有找到匹配的 profile，
        也能通过旧的实现逻辑构建出一个 profile。
        """
        vocab_strategy = build_vocabulary_prompt_strategy(plan)
        grammar_strategy = build_grammar_prompt_strategy(plan)
        translation_strategy = build_translation_prompt_strategy(plan)

        from app.services.analysis.prompting.example_strategy import (
            get_grammar_example_strategy,
            get_translation_example_strategy,
            get_vocabulary_example_strategy,
        )

        vocab_examples = get_vocabulary_example_strategy(plan)
        grammar_examples = get_grammar_example_strategy(plan)
        translation_examples = get_translation_example_strategy(plan)

        policy_config = PromptPolicyConfig(
            vocabulary=vocab_strategy.policy_lines,
            grammar=grammar_strategy.policy_lines,
            translation=translation_strategy.policy_lines,
        )

        example_config = ExampleConfig(
            vocabulary=tuple(vocab_examples.examples),
            grammar=tuple(grammar_examples.examples),
            translation=tuple(translation_examples.examples),
            selection_mode=vocab_examples.selection_mode,
        )

        from app.services.analysis.prompting.profiles.models import ProfileVersion

        return PromptProfile(
            profile_id=plan.prompt_profile,
            version=ProfileVersion(major=0, minor=0, patch=0, is_default=True),
            description="Legacy fallback profile (built from old implementation)",
            reading_goal=plan.goal_id,
            reading_variant=plan.variant_id,
            policy_config=policy_config,
            example_config=example_config,
            goal_policy=plan.policy,
        )

    def get_strategy_bundle(
        self,
        plan: GoalExecutionPlan,
        agent_type: Literal["vocabulary", "grammar", "translation", "term", "academic_translation", "understanding"],
        version: str | None = None,
    ) -> StrategyBundle:
        """获取指定 agent 的策略 bundle。

        这是一个便捷方法，根据 agent_type 从解析出的 profile 中构建 StrategyBundle。

        Args:
            plan: 执行计划
            agent_type: agent 类型
            version: 可选的版本号

        Returns:
            StrategyBundle 实例
        """
        result = self.resolve_or_fallback(plan, version)
        profile = result.profile

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


class ResolutionSource:
    """解析结果来源。"""

    REGISTRY = "registry"
    LEGACY = "legacy"


class ProfileResolutionResult:
    """Profile 解析结果。

    包含解析出的 profile 和来源标识，便于追踪和调试。
    """

    def __init__(
        self,
        profile: PromptProfile,
        source: Literal["registry", "legacy"],
        plan: GoalExecutionPlan,
    ) -> None:
        self.profile = profile
        self.source = source
        self.plan = plan

    @property
    def is_from_registry(self) -> bool:
        """是否来自注册中心。"""
        return self.source == ResolutionSource.REGISTRY

    @property
    def is_from_legacy(self) -> bool:
        """是否来自旧的实现（回退）。"""
        return self.source == ResolutionSource.LEGACY


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
) -> ProfileResolutionResult:
    """使用默认解析器解析 profile。

    这是一个便捷函数，等价于：
        get_default_resolver().resolve_or_fallback(plan, version)
    """
    return get_default_resolver().resolve_or_fallback(plan, version)

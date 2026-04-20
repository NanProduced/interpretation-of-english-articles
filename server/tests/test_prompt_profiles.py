"""测试新的声明式 Prompt Profile 体系。

验证以下功能：
1. 核心数据模型的正确性
2. ProfileRegistry 的注册、查询、版本管理功能
3. ProfileResolver 的解析功能和兼容性
4. 内置 profiles 与旧实现的行为一致性
5. 版本化功能（同一 profile 的不同版本）
"""

from __future__ import annotations

from typing import Literal

import pytest

from app.schemas.internal.execution_plan import GoalExecutionPlan, GoalPolicy
from app.services.analysis.planning.goal_planner import build_goal_execution_plan
from app.services.analysis.prompting.example_strategy import (
    BEGINNER_VOCABULARY_EXAMPLES,
    ExampleEntry,
    ExampleStrategy,
    get_vocabulary_example_strategy,
)
from app.services.analysis.prompting.profiles import (
    ExampleConfig,
    ProfileRegistry,
    ProfileResolutionResult,
    ProfileResolver,
    ProfileVersion,
    PromptPolicyConfig,
    PromptProfile,
    get_builtin_profiles,
    get_default_registry,
    init_profiles,
    register_profile,
    resolve_profile,
    resolve_version,
)
from app.services.analysis.prompting.prompt_strategy import (
    PromptStrategy,
    build_vocabulary_prompt_strategy,
)
from app.services.analysis.prompting.strategy_builder import (
    StrategyBundle,
    build_strategy_bundle,
    build_vocabulary_bundle,
)


class TestProfileVersion:
    """测试 ProfileVersion 类。"""

    def test_from_string_with_semantic_version(self) -> None:
        version = ProfileVersion.from_string("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert not version.is_default

    def test_from_string_with_default(self) -> None:
        version = ProfileVersion.from_string("default")
        assert version.is_default
        assert version.to_string() == "default"

    def test_to_string(self) -> None:
        assert ProfileVersion(major=1, minor=2, patch=3).to_string() == "1.2.3"
        assert ProfileVersion(major=1, minor=0, patch=0).to_string() == "1.0.0"

    def test_matches_exact(self) -> None:
        version = ProfileVersion(major=1, minor=2, patch=3)
        assert version.matches("1.2.3")
        assert version.matches(ProfileVersion(major=1, minor=2, patch=3))

    def test_matches_partial(self) -> None:
        version = ProfileVersion(major=1, minor=2, patch=3)
        assert version.matches("1")
        assert version.matches("1.2")
        assert not version.matches("2")
        assert not version.matches("1.3")

    def test_comparison(self) -> None:
        v1 = ProfileVersion(major=1, minor=0, patch=0)
        v2 = ProfileVersion(major=1, minor=1, patch=0)
        v3 = ProfileVersion(major=2, minor=0, patch=0)
        default = ProfileVersion(major=0, minor=0, patch=0, is_default=True)

        assert v1 < v2
        assert v2 < v3
        assert default > v3

    def test_equality(self) -> None:
        v1 = ProfileVersion(major=1, minor=2, patch=3)
        v2 = ProfileVersion(major=1, minor=2, patch=3)
        v3 = ProfileVersion(major=1, minor=2, patch=4)
        default1 = ProfileVersion(major=0, minor=0, patch=0, is_default=True)
        default2 = ProfileVersion(major=0, minor=0, patch=0, is_default=True)

        assert v1 == v2
        assert v1 != v3
        assert default1 == default2
        assert v1 != default1


class TestResolveVersion:
    """测试 resolve_version 函数。"""

    def test_resolve_default(self) -> None:
        versions = [
            ProfileVersion(major=1, minor=0, patch=0),
            ProfileVersion(major=2, minor=0, patch=0, is_default=True),
            ProfileVersion(major=1, minor=1, patch=0),
        ]

        result = resolve_version(versions)
        assert result is not None
        assert result.is_default

    def test_resolve_latest_when_no_default(self) -> None:
        versions = [
            ProfileVersion(major=1, minor=0, patch=0),
            ProfileVersion(major=2, minor=0, patch=0),
            ProfileVersion(major=1, minor=1, patch=0),
        ]

        result = resolve_version(versions)
        assert result is not None
        assert result.major == 2

    def test_resolve_specific_version(self) -> None:
        versions = [
            ProfileVersion(major=1, minor=0, patch=0),
            ProfileVersion(major=1, minor=1, patch=0),
            ProfileVersion(major=2, minor=0, patch=0),
        ]

        result = resolve_version(versions, "1.1")
        assert result is not None
        assert result.major == 1
        assert result.minor == 1

    def test_resolve_returns_none_for_unknown_version(self) -> None:
        versions = [
            ProfileVersion(major=1, minor=0, patch=0),
            ProfileVersion(major=2, minor=0, patch=0),
        ]

        result = resolve_version(versions, "3")
        assert result is None

    def test_resolve_empty_list(self) -> None:
        result = resolve_version([])
        assert result is None


class TestPromptProfile:
    """测试 PromptProfile 类。"""

    def test_create_profile(self) -> None:
        version = ProfileVersion(major=1, minor=0, patch=0, is_default=True)
        policy_config = PromptPolicyConfig(
            vocabulary=("policy line 1", "policy line 2"),
            grammar=("grammar policy",),
            translation=("translation policy",),
        )
        example_config = ExampleConfig(
            vocabulary=(
                ExampleEntry(
                    example_type="vocab",
                    sentence_text="Test sentence",
                    output_fragment='{"type": "vocab_highlight"}',
                ),
            ),
        )

        profile = PromptProfile(
            profile_id="test_profile",
            version=version,
            description="Test profile",
            reading_goal="daily",
            reading_variant="beginner_reading",
            policy_config=policy_config,
            example_config=example_config,
        )

        assert profile.profile_id == "test_profile"
        assert profile.is_default
        assert profile.get_policy_lines("vocabulary") == ("policy line 1", "policy line 2")
        assert len(profile.get_examples("vocabulary")) == 1

    def test_get_policy_lines_returns_empty_for_unknown_type(self) -> None:
        profile = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )

        assert profile.get_policy_lines("unknown") == ()

    def test_get_examples_returns_empty_for_unknown_type(self) -> None:
        profile = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )

        assert profile.get_examples("unknown") == []


class TestProfileRegistry:
    """测试 ProfileRegistry 类。"""

    def test_register_and_get(self) -> None:
        registry = ProfileRegistry()
        profile = PromptProfile(
            profile_id="test_profile",
            version=ProfileVersion(major=1, minor=0, patch=0, is_default=True),
            description="Test profile",
        )

        registry.register(profile)

        retrieved = registry.get("test_profile")
        assert retrieved is not None
        assert retrieved.profile_id == "test_profile"

    def test_register_duplicate_version_raises_error(self) -> None:
        registry = ProfileRegistry()
        profile1 = PromptProfile(
            profile_id="test_profile",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        profile2 = PromptProfile(
            profile_id="test_profile",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )

        registry.register(profile1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register(profile2)

    def test_get_by_version(self) -> None:
        registry = ProfileRegistry()
        v1 = PromptProfile(
            profile_id="test_profile",
            version=ProfileVersion(major=1, minor=0, patch=0),
            description="Version 1.0.0",
        )
        v2 = PromptProfile(
            profile_id="test_profile",
            version=ProfileVersion(major=2, minor=0, patch=0, is_default=True),
            description="Version 2.0.0",
        )

        registry.register(v1)
        registry.register(v2)

        default = registry.get("test_profile")
        assert default is not None
        assert default.version.major == 2

        v1_retrieved = registry.get("test_profile", "1")
        assert v1_retrieved is not None
        assert v1_retrieved.version.major == 1

    def test_has_profile(self) -> None:
        registry = ProfileRegistry()
        assert not registry.has_profile("nonexistent")

        profile = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        registry.register(profile)

        assert registry.has_profile("test")

    def test_has_version(self) -> None:
        registry = ProfileRegistry()
        profile = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        registry.register(profile)

        assert registry.has_version("test", "1")
        assert registry.has_version("test", "1.0")
        assert registry.has_version("test", "1.0.0")
        assert not registry.has_version("test", "2")

    def test_list_profile_ids(self) -> None:
        registry = ProfileRegistry()
        registry.register(
            PromptProfile(
                profile_id="profile1",
                version=ProfileVersion(major=1, minor=0, patch=0),
            )
        )
        registry.register(
            PromptProfile(
                profile_id="profile2",
                version=ProfileVersion(major=1, minor=0, patch=0),
            )
        )

        profile_ids = registry.list_profile_ids()
        assert "profile1" in profile_ids
        assert "profile2" in profile_ids
        assert len(profile_ids) == 2

    def test_unregister_specific_version(self) -> None:
        registry = ProfileRegistry()
        v1 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        v2 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=2, minor=0, patch=0, is_default=True),
        )

        registry.register(v1)
        registry.register(v2)

        registry.unregister("test", "1")

        assert registry.has_profile("test")
        assert registry.get("test") is not None
        assert registry.get("test", "1") is None

    def test_unregister_all_versions(self) -> None:
        registry = ProfileRegistry()
        v1 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        v2 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=2, minor=0, patch=0),
        )

        registry.register(v1)
        registry.register(v2)

        registry.unregister("test")

        assert not registry.has_profile("test")

    def test_set_default_version(self) -> None:
        registry = ProfileRegistry()
        v1 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        v2 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=2, minor=0, patch=0),
        )

        registry.register(v1)
        registry.register(v2)

        default = registry.get_default_version("test")
        assert default is not None
        assert default.major == 1

        registry.set_default_version("test", "2")

        new_default = registry.get_default_version("test")
        assert new_default is not None
        assert new_default.major == 2

    def test_bulk_register(self) -> None:
        registry = ProfileRegistry()
        profiles = [
            PromptProfile(
                profile_id=f"profile{i}",
                version=ProfileVersion(major=1, minor=0, patch=0),
            )
            for i in range(3)
        ]

        registry.bulk_register(profiles)

        assert len(registry.list_profile_ids()) == 3


class TestBuiltinProfiles:
    """测试内置 profiles。"""

    def test_get_builtin_profiles_returns_profiles(self) -> None:
        profiles = get_builtin_profiles()
        assert len(profiles) > 0

        profile_ids = [p.profile_id for p in profiles]
        assert "daily_beginner" in profile_ids
        assert "daily_intermediate" in profile_ids
        assert "daily_intensive" in profile_ids
        assert "exam_gaokao" in profile_ids
        assert "exam_cet" in profile_ids
        assert "exam_kaoyan" in profile_ids
        assert "exam_tem" in profile_ids
        assert "exam_ielts_toefl" in profile_ids

    def test_init_profiles_registers_builtin_profiles(self) -> None:
        registry = get_default_registry()
        registry.unregister("daily_beginner") if registry.has_profile("daily_beginner") else None

        assert not registry.has_profile("daily_beginner")

        init_profiles()

        assert registry.has_profile("daily_beginner")

    def test_init_profiles_is_idempotent(self) -> None:
        registry = get_default_registry()
        init_profiles()
        count_before = len(registry.list_profiles())

        init_profiles()

        count_after = len(registry.list_profiles())
        assert count_before == count_after


class TestProfileResolver:
    """测试 ProfileResolver 类。"""

    def test_resolve_from_registry(self) -> None:
        init_profiles()
        resolver = ProfileResolver()
        plan = build_goal_execution_plan("daily_reading", "beginner_reading")

        result = resolver.resolve_or_fallback(plan)

        assert result.is_from_registry
        assert result.profile.profile_id == "daily_beginner"

    def test_get_strategy_bundle(self) -> None:
        init_profiles()
        resolver = ProfileResolver()
        plan = build_goal_execution_plan("daily_reading", "beginner_reading")

        bundle = resolver.get_strategy_bundle(plan, "vocabulary")

        assert isinstance(bundle, StrategyBundle)
        assert isinstance(bundle.prompt_strategy, PromptStrategy)
        assert isinstance(bundle.example_strategy, ExampleStrategy)

    def test_resolve_profile_convenience_function(self) -> None:
        init_profiles()
        plan = build_goal_execution_plan("daily_reading", "intermediate_reading")

        result = resolve_profile(plan)

        assert isinstance(result, ProfileResolutionResult)
        assert result.profile.profile_id == "daily_intermediate"


class TestCompatibility:
    """测试新体系与旧实现的兼容性。"""

    def test_builtin_profile_policy_lines_match_old_implementation(self) -> None:
        """验证内置 profile 的 policy lines 与旧实现一致。"""
        init_profiles()
        plan = build_goal_execution_plan("daily_reading", "beginner_reading")

        old_strategy = build_vocabulary_prompt_strategy(plan)

        resolver = ProfileResolver()
        result = resolver.resolve_or_fallback(plan)
        new_policy_lines = result.profile.get_policy_lines("vocabulary")

        assert old_strategy.policy_lines == new_policy_lines

    def test_builtin_profile_examples_match_old_implementation(self) -> None:
        """验证内置 profile 的 examples 与旧实现一致。"""
        init_profiles()
        plan = build_goal_execution_plan("daily_reading", "beginner_reading")

        old_examples = get_vocabulary_example_strategy(plan)

        resolver = ProfileResolver()
        result = resolver.resolve_or_fallback(plan)
        new_examples = result.profile.get_examples("vocabulary")

        assert len(old_examples.examples) == len(new_examples)
        for old, new in zip(old_examples.examples, new_examples):
            assert old.example_type == new.example_type
            assert old.sentence_text == new.sentence_text
            assert old.output_fragment == new.output_fragment

    def test_strategy_builder_without_version_uses_old_implementation(self) -> None:
        """验证不指定 version 时使用旧实现（保持兼容）。"""
        plan = build_goal_execution_plan("daily_reading", "beginner_reading")

        bundle = build_vocabulary_bundle(plan)

        expected_policy = build_vocabulary_prompt_strategy(plan)
        expected_examples = get_vocabulary_example_strategy(plan)

        assert bundle.prompt_strategy.policy_lines == expected_policy.policy_lines
        assert len(bundle.example_strategy.examples) == len(expected_examples.examples)

    def test_strategy_builder_with_version_uses_new_system(self) -> None:
        """验证指定 version 时使用新的 profile 体系。"""
        init_profiles()
        plan = build_goal_execution_plan("daily_reading", "beginner_reading")

        bundle = build_vocabulary_bundle(plan, profile_version="default")

        registry = get_default_registry()
        expected_profile = registry.get("daily_beginner", "default")
        assert expected_profile is not None

        assert bundle.prompt_strategy.policy_lines == expected_profile.get_policy_lines("vocabulary")
        assert len(bundle.example_strategy.examples) == len(expected_profile.get_examples("vocabulary"))

    def test_build_strategy_bundle_convenience_function(self) -> None:
        """测试通用的 build_strategy_bundle 函数。"""
        init_profiles()
        plan = build_goal_execution_plan("daily_reading", "intermediate_reading")

        vocab_bundle = build_strategy_bundle(plan, "vocabulary", profile_version="default")
        grammar_bundle = build_strategy_bundle(plan, "grammar", profile_version="default")
        translation_bundle = build_strategy_bundle(plan, "translation", profile_version="default")

        assert isinstance(vocab_bundle, StrategyBundle)
        assert isinstance(grammar_bundle, StrategyBundle)
        assert isinstance(translation_bundle, StrategyBundle)


class TestVersioning:
    """测试版本化功能。"""

    def test_same_profile_different_versions(self) -> None:
        """测试同一 profile 的不同版本。"""
        registry = ProfileRegistry()

        v1 = PromptProfile(
            profile_id="test_profile",
            version=ProfileVersion(major=1, minor=0, patch=0),
            description="Version 1",
            policy_config=PromptPolicyConfig(
                vocabulary=("v1 policy",),
            ),
        )

        v2 = PromptProfile(
            profile_id="test_profile",
            version=ProfileVersion(major=2, minor=0, patch=0, is_default=True),
            description="Version 2",
            policy_config=PromptPolicyConfig(
                vocabulary=("v2 policy",),
            ),
        )

        registry.register(v1)
        registry.register(v2)

        default = registry.get("test_profile")
        assert default is not None
        assert default.get_policy_lines("vocabulary") == ("v2 policy",)

        v1_retrieved = registry.get("test_profile", "1")
        assert v1_retrieved is not None
        assert v1_retrieved.get_policy_lines("vocabulary") == ("v1 policy",)

    def test_register_new_version_does_not_change_default(self) -> None:
        """测试注册新版本时不会自动改变默认版本。

        设计原则：
        - 第一个注册的版本自动成为默认版本
        - 后续注册的版本不会自动改变默认版本
        - 要改变默认版本，需要显式使用 set_default_version 或注册时标记 is_default=True
        """
        registry = ProfileRegistry()

        v1 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        registry.register(v1)

        default = registry.get_default_version("test")
        assert default is not None
        assert default.major == 1

        v2 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=2, minor=0, patch=0),
        )
        registry.register(v2)

        new_default = registry.get_default_version("test")
        assert new_default is not None
        assert new_default.major == 1

    def test_register_with_is_default_flag_changes_default(self) -> None:
        """测试注册时显式标记 is_default=True 会改变默认版本。"""
        registry = ProfileRegistry()

        v1 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )
        registry.register(v1)

        default = registry.get_default_version("test")
        assert default is not None
        assert default.major == 1

        v2 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=2, minor=0, patch=0, is_default=True),
        )
        registry.register(v2)

        new_default = registry.get_default_version("test")
        assert new_default is not None
        assert new_default.major == 2

    def test_explicit_default_version(self) -> None:
        """测试显式标记为默认版本。"""
        registry = ProfileRegistry()

        v2 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=2, minor=0, patch=0, is_default=True),
        )
        v1 = PromptProfile(
            profile_id="test",
            version=ProfileVersion(major=1, minor=0, patch=0),
        )

        registry.register(v2)
        registry.register(v1)

        default = registry.get_default_version("test")
        assert default is not None
        assert default.major == 2

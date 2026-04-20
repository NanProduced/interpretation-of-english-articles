"""声明式 Prompt Profile 体系。

该模块提供了一套声明式、可版本化、可扩展的 prompt profile 管理机制。

核心概念：
- ProfileVersion: 版本信息，支持语义化版本和默认版本
- PromptPolicyConfig: Prompt 策略配置，包含不同 agent 的 policy lines
- ExampleConfig: Example 配置，包含不同 agent 的 few-shot 示例
- PromptProfile: 完整的 profile 定义，聚合所有配置
- ProfileRegistry: Profile 注册中心，支持注册、查询、版本管理
- ProfileResolver: Profile 解析器，根据执行计划解析出对应的 profile

设计原则：
1. 声明式配置：所有配置都是数据驱动的，不包含逻辑代码
2. 版本化：每个 profile 可以有多个版本，支持语义化版本查询
3. 可扩展：通过注册机制支持动态添加新的 profile
4. 统一路径：不再有 legacy fallback 路径，所有配置都来自注册中心

使用示例：
    # 获取默认解析器
    from app.services.analysis.prompting.profiles import resolve_profile, init_profiles
    
    # 在应用启动时初始化内置 profiles
    init_profiles()
    
    # 解析 profile
    profile = resolve_profile(execution_plan)
    
    # 获取指定 agent 的 policy lines
    vocab_policy = profile.get_policy_lines("vocabulary")
    
    # 获取示例
    vocab_examples = profile.get_examples("vocabulary")
"""

from app.services.analysis.prompting.profiles.builtin_profiles import (
    get_builtin_profiles,
    register_builtin_profiles,
)
from app.services.analysis.prompting.profiles.models import (
    ExampleConfig,
    ProfileVersion,
    PromptPolicyConfig,
    PromptProfile,
    resolve_version,
)
from app.services.analysis.prompting.profiles.registry import (
    ProfileRegistry,
    get_default_registry,
    register_profile,
)
from app.services.analysis.prompting.profiles.resolver import (
    ProfileResolver,
    resolve_profile,
)


def init_profiles() -> None:
    """初始化 profile 体系。

    在应用启动时调用此函数，确保所有内置 profile 都已注册。
    此函数可以安全地多次调用（通过检查注册中心状态避免重复注册）。
    """
    registry = get_default_registry()
    if not registry.has_profile("daily_beginner"):
        register_builtin_profiles()


__all__ = [
    "ExampleConfig",
    "ProfileRegistry",
    "ProfileResolver",
    "ProfileVersion",
    "PromptPolicyConfig",
    "PromptProfile",
    "get_builtin_profiles",
    "get_default_registry",
    "init_profiles",
    "register_builtin_profiles",
    "register_profile",
    "resolve_profile",
    "resolve_version",
]

"""Prompt Profile 核心数据模型。

定义了声明式、可版本化的 prompt profile 数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.schemas.internal.execution_plan import GoalPolicy
from app.services.analysis.prompting.example_strategy import ExampleEntry


@dataclass(frozen=True, slots=True)
class ProfileVersion:
    """Profile 版本信息。

    支持语义化版本，同时支持 "default" 作为默认版本标识。

    Attributes:
        major: 主版本号
        minor: 次版本号
        patch: 修订号
        is_default: 是否为默认版本
    """

    major: int
    minor: int = 0
    patch: int = 0
    is_default: bool = False

    @classmethod
    def from_string(cls, version_str: str) -> ProfileVersion:
        """从字符串解析版本号。

        Args:
            version_str: 版本字符串，如 "1.0.0" 或 "default"

        Returns:
            ProfileVersion 实例
        """
        if version_str.lower() == "default":
            return cls(major=0, minor=0, patch=0, is_default=True)

        parts = version_str.split(".")
        major = int(parts[0]) if parts else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return cls(major=major, minor=minor, patch=patch)

    def to_string(self) -> str:
        """转换为字符串表示。"""
        if self.is_default:
            return "default"
        return f"{self.major}.{self.minor}.{self.patch}"

    def matches(self, other: ProfileVersion | str) -> bool:
        """检查版本是否匹配。

        支持部分匹配：
        - "1" 匹配所有 1.x.x 版本
        - "1.0" 匹配所有 1.0.x 版本
        - "1.0.0" 精确匹配
        """
        if isinstance(other, str):
            other = ProfileVersion.from_string(other)

        if other.is_default:
            return self.is_default

        if self.major != other.major:
            return False

        if other.minor > 0 and self.minor != other.minor:
            return False

        if other.patch > 0 and self.patch != other.patch:
            return False

        return True

    def __lt__(self, other: ProfileVersion) -> bool:
        if self.is_default:
            return False
        if other.is_default:
            return True
        if self.major != other.major:
            return self.major < other.major
        if self.minor != other.minor:
            return self.minor < other.minor
        return self.patch < other.patch

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ProfileVersion):
            return False
        if self.is_default or other.is_default:
            return self.is_default == other.is_default
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )

    def __hash__(self) -> int:
        if self.is_default:
            return hash("default")
        return hash((self.major, self.minor, self.patch))


@dataclass(frozen=True, slots=True)
class PromptPolicyConfig:
    """Prompt 策略配置。

    包含不同 agent 的 policy lines 配置。

    Attributes:
        vocabulary: 词汇标注 agent 的 policy lines
        grammar: 语法分析 agent 的 policy lines
        translation: 翻译 agent 的 policy lines
        term: 术语标注 agent 的 policy lines（academic workflow）
        academic_translation: 学术翻译 agent 的 policy lines（academic workflow）
        understanding: 理解/逻辑标注 agent 的 policy lines（academic workflow）
    """

    vocabulary: tuple[str, ...] = ()
    grammar: tuple[str, ...] = ()
    translation: tuple[str, ...] = ()
    term: tuple[str, ...] = ()
    academic_translation: tuple[str, ...] = ()
    understanding: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExampleConfig:
    """Example 配置。

    包含不同 agent 的 few-shot 示例配置。

    Attributes:
        vocabulary: 词汇标注 agent 的示例
        grammar: 语法分析 agent 的示例
        translation: 翻译 agent 的示例
        term: 术语标注 agent 的示例（academic workflow）
        academic_translation: 学术翻译 agent 的示例（academic workflow）
        understanding: 理解/逻辑标注 agent 的示例（academic workflow）
        selection_mode: 示例选择模式
    """

    vocabulary: tuple[ExampleEntry, ...] = ()
    grammar: tuple[ExampleEntry, ...] = ()
    translation: tuple[ExampleEntry, ...] = ()
    term: tuple[ExampleEntry, ...] = ()
    academic_translation: tuple[ExampleEntry, ...] = ()
    understanding: tuple[ExampleEntry, ...] = ()
    selection_mode: Literal["baseline", "rag", "manual"] = "baseline"


@dataclass(frozen=True, slots=True)
class PromptProfile:
    """Prompt Profile 完整定义。

    一个 profile 定义了一组 prompt 配置，包含：
    - 版本信息
    - 元数据（描述、适用场景等）
    - Prompt 策略配置
    - Example 配置
    - 后处理策略（可选）

    Attributes:
        profile_id: Profile 唯一标识
        version: 版本信息
        description: 描述信息
        reading_goal: 适用的阅读目标
        reading_variant: 适用的阅读变体
        policy_config: Prompt 策略配置
        example_config: Example 配置
        goal_policy: 后处理硬策略（可选）
    """

    profile_id: str
    version: ProfileVersion
    description: str = ""
    reading_goal: str | None = None
    reading_variant: str | None = None
    policy_config: PromptPolicyConfig = field(default_factory=PromptPolicyConfig)
    example_config: ExampleConfig = field(default_factory=ExampleConfig)
    goal_policy: GoalPolicy | None = None

    @property
    def is_default(self) -> bool:
        """是否为默认版本。"""
        return self.version.is_default

    def get_policy_lines(
        self,
        agent_type: Literal["vocabulary", "grammar", "translation", "term", "academic_translation", "understanding"],
    ) -> tuple[str, ...]:
        """获取指定 agent 的 policy lines。"""
        if agent_type == "vocabulary":
            return self.policy_config.vocabulary
        elif agent_type == "grammar":
            return self.policy_config.grammar
        elif agent_type == "translation":
            return self.policy_config.translation
        elif agent_type == "term":
            return self.policy_config.term
        elif agent_type == "academic_translation":
            return self.policy_config.academic_translation
        elif agent_type == "understanding":
            return self.policy_config.understanding
        return ()

    def get_examples(
        self,
        agent_type: Literal["vocabulary", "grammar", "translation", "term", "academic_translation", "understanding"],
    ) -> list[ExampleEntry]:
        """获取指定 agent 的示例列表。"""
        if agent_type == "vocabulary":
            return list(self.example_config.vocabulary)
        elif agent_type == "grammar":
            return list(self.example_config.grammar)
        elif agent_type == "translation":
            return list(self.example_config.translation)
        elif agent_type == "term":
            return list(self.example_config.term)
        elif agent_type == "academic_translation":
            return list(self.example_config.academic_translation)
        elif agent_type == "understanding":
            return list(self.example_config.understanding)
        return []


def resolve_version(
    versions: list[ProfileVersion],
    requested_version: str | ProfileVersion | None = None,
) -> ProfileVersion | None:
    """从版本列表中解析出匹配的版本。

    Args:
        versions: 可用的版本列表
        requested_version: 请求的版本，可为 None（使用默认版本）

    Returns:
        匹配的版本，若无匹配则返回 None
    """
    if not versions:
        return None

    if requested_version is None:
        default_versions = [v for v in versions if v.is_default]
        if default_versions:
            return default_versions[0]
        sorted_versions = sorted(versions, reverse=True)
        return sorted_versions[0]

    if isinstance(requested_version, str):
        requested_version = ProfileVersion.from_string(requested_version)

    candidates = [v for v in versions if v.matches(requested_version)]
    if not candidates:
        return None

    sorted_candidates = sorted(candidates, reverse=True)
    return sorted_candidates[0]

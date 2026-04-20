"""Profile 注册中心。

提供统一的 profile 注册、查询、版本管理机制。
"""

from __future__ import annotations

from typing import Iterable

from app.services.analysis.prompting.profiles.models import (
    ProfileVersion,
    PromptProfile,
    resolve_version,
)


class ProfileRegistry:
    """Profile 注册中心。

    管理所有已注册的 prompt profile，支持：
    - 按 profile_id 注册
    - 按 profile_id 和可选版本查询
    - 列出所有可用的 profile
    - 管理默认版本

    设计原则：
    1. 每个 profile_id 可以有多个版本
    2. 每个 profile_id 有且仅有一个默认版本
    3. 未指定版本时返回默认版本
    """

    def __init__(self) -> None:
        self._profiles: dict[str, dict[ProfileVersion, PromptProfile]] = {}
        self._default_versions: dict[str, ProfileVersion] = {}

    def register(self, profile: PromptProfile) -> None:
        """注册一个 profile。

        Args:
            profile: 要注册的 profile

        Raises:
            ValueError: 如果同一个 profile_id 下已有同名版本
        """
        profile_id = profile.profile_id
        version = profile.version

        if profile_id not in self._profiles:
            self._profiles[profile_id] = {}

        if version in self._profiles[profile_id]:
            raise ValueError(
                f"Profile '{profile_id}' version '{version.to_string()}' already registered"
            )

        self._profiles[profile_id][version] = profile

        if version.is_default or profile_id not in self._default_versions:
            self._default_versions[profile_id] = version

    def get(
        self,
        profile_id: str,
        version: str | ProfileVersion | None = None,
    ) -> PromptProfile | None:
        """获取指定的 profile。

        Args:
            profile_id: Profile 唯一标识
            version: 版本号，可选。支持：
                - None: 返回默认版本
                - "default": 返回默认版本
                - "1": 返回 1.x.x 中最新的版本
                - "1.0": 返回 1.0.x 中最新的版本
                - "1.0.0": 返回精确匹配的版本

        Returns:
            匹配的 profile，若无则返回 None
        """
        if profile_id not in self._profiles:
            return None

        version_map = self._profiles[profile_id]
        available_versions = list(version_map.keys())

        resolved_version = resolve_version(available_versions, version)
        if resolved_version is None:
            return None

        return version_map.get(resolved_version)

    def get_all_versions(self, profile_id: str) -> list[PromptProfile]:
        """获取指定 profile_id 的所有版本。

        Args:
            profile_id: Profile 唯一标识

        Returns:
            所有版本的列表，按版本号降序排列
        """
        if profile_id not in self._profiles:
            return []

        version_map = self._profiles[profile_id]
        profiles = list(version_map.values())
        profiles.sort(key=lambda p: p.version, reverse=True)
        return profiles

    def list_profile_ids(self) -> list[str]:
        """列出所有已注册的 profile_id。"""
        return list(self._profiles.keys())

    def list_profiles(self) -> list[PromptProfile]:
        """列出所有已注册的 profile（所有版本）。"""
        all_profiles: list[PromptProfile] = []
        for version_map in self._profiles.values():
            all_profiles.extend(version_map.values())
        return all_profiles

    def has_profile(self, profile_id: str) -> bool:
        """检查是否存在指定的 profile_id。"""
        return profile_id in self._profiles

    def has_version(self, profile_id: str, version: str | ProfileVersion) -> bool:
        """检查指定 profile_id 是否有指定版本。

        Args:
            profile_id: Profile 唯一标识
            version: 版本号

        Returns:
            是否存在该版本
        """
        if profile_id not in self._profiles:
            return False

        if isinstance(version, str):
            version = ProfileVersion.from_string(version)

        return version in self._profiles[profile_id]

    def get_default_version(self, profile_id: str) -> ProfileVersion | None:
        """获取指定 profile_id 的默认版本。"""
        return self._default_versions.get(profile_id)

    def set_default_version(self, profile_id: str, version: str | ProfileVersion) -> None:
        """设置指定 profile_id 的默认版本。

        Args:
            profile_id: Profile 唯一标识
            version: 版本号

        Raises:
            ValueError: 如果 profile_id 或版本不存在
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' not found")

        if isinstance(version, str):
            version = ProfileVersion.from_string(version)

        if version not in self._profiles[profile_id]:
            raise ValueError(
                f"Version '{version.to_string()}' not found for profile '{profile_id}'"
            )

        self._default_versions[profile_id] = version

    def unregister(self, profile_id: str, version: str | ProfileVersion | None = None) -> None:
        """注销一个 profile 或其特定版本。

        Args:
            profile_id: Profile 唯一标识
            version: 版本号，可选。如果为 None，则注销该 profile_id 的所有版本

        Raises:
            ValueError: 如果 profile_id 或版本不存在
        """
        if profile_id not in self._profiles:
            raise ValueError(f"Profile '{profile_id}' not found")

        if version is None:
            del self._profiles[profile_id]
            self._default_versions.pop(profile_id, None)
            return

        if isinstance(version, str):
            version = ProfileVersion.from_string(version)

        if version not in self._profiles[profile_id]:
            raise ValueError(
                f"Version '{version.to_string()}' not found for profile '{profile_id}'"
            )

        del self._profiles[profile_id][version]

        if not self._profiles[profile_id]:
            del self._profiles[profile_id]
            self._default_versions.pop(profile_id, None)
            return

        if self._default_versions.get(profile_id) == version:
            remaining_versions = list(self._profiles[profile_id].keys())
            default_versions = [v for v in remaining_versions if v.is_default]
            if default_versions:
                self._default_versions[profile_id] = default_versions[0]
            else:
                sorted_versions = sorted(remaining_versions, reverse=True)
                self._default_versions[profile_id] = sorted_versions[0]

    def bulk_register(self, profiles: Iterable[PromptProfile]) -> None:
        """批量注册 profile。

        Args:
            profiles: 要注册的 profile 列表
        """
        for profile in profiles:
            self.register(profile)


_default_registry: ProfileRegistry | None = None


def get_default_registry() -> ProfileRegistry:
    """获取默认的全局注册中心实例。"""
    global _default_registry
    if _default_registry is None:
        _default_registry = ProfileRegistry()
    return _default_registry


def register_profile(profile: PromptProfile) -> None:
    """向默认注册中心注册 profile。

    这是一个便捷函数，等价于：
        get_default_registry().register(profile)
    """
    get_default_registry().register(profile)

"""
词典服务

提供统一的词典查询入口，处理查询词归一化。
MVP 阶段仅使用本地 ECDICT 词典。
"""

from __future__ import annotations

from typing import Any

from app.services.dictionary.providers import EcdictProvider


class LookupError(Exception):
    """词典查询失败（词不存在）"""
    pass


class DictionaryService:
    """
    词典服务

    MVP 阶段仅使用本地 ECDICT 词典，不再依赖第三方在线 API。
    """

    # Alias 归一化映射
    _ALIAS_MAP: dict[str, str] = {
        "u.s.": "us",
        "u.k.": "uk",
        "e.g.": "eg",
        "i.e.": "ie",
        "prof.": "prof",
        "dr.": "dr",
        "mr.": "mr",
        "mrs.": "mrs",
        "ms.": "ms",
        "vs.": "vs",
        "etc.": "etc",
    }

    def __init__(self) -> None:
        self._provider = EcdictProvider()

    async def lookup(self, word: str) -> dict[str, Any]:
        """
        查询单词释义。

        流程：
        1. 归一化查询词（trim + lowercase + alias 映射）
        2. 使用 ECDICT 本地 provider 查询
        3. 未命中则抛出 LookupError

        Args:
            word: 原始查询词

        Returns:
            DictionaryResult 字典

        Raises:
            LookupError: 词不存在或查询失败
        """
        normalized = self._normalize(word)
        try:
            return await self._provider.fetch(normalized)
        except ValueError:
            raise LookupError(f"Word not found: {word}") from None

    def _normalize(self, word: str) -> str:
        """
        归一化查询词。

        1. trim 去除首尾空白
        2. lowercase 转为小写
        3. alias 映射处理缩写

        Args:
            word: 原始查询词

        Returns:
            归一化后的查询词
        """
        normalized = word.strip().lower()

        # alias 归一化
        if normalized in self._ALIAS_MAP:
            normalized = self._ALIAS_MAP[normalized]

        return normalized


# 服务单例
_service: DictionaryService | None = None


def get_service() -> DictionaryService:
    """获取 DictionaryService 单例"""
    global _service
    if _service is None:
        _service = DictionaryService()
    return _service

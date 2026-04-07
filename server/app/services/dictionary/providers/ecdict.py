"""
ECDICT 本地词典 Provider

使用 PostgreSQL 数据库提供词典查询服务。
"""

from __future__ import annotations

import re
from typing import Any

from app.services.dictionary.cache import get as cache_get
from app.services.dictionary.cache import set as cache_set
from app.services.dictionary.db_pg import EntryRow, full_lookup
from app.services.dictionary.schemas import (
    DictionaryMeaning,
    DictionaryMeaningDefinition,
    DictionaryResult,
    EcdictEntry,
)


class EcdictProvider:
    """ECDICT 本地词典 Provider"""

    async def fetch(self, word: str) -> dict[str, Any]:
        """
        查询单词释义。

        优先查缓存；缓存未命中则查询 PostgreSQL。

        Args:
            word: 归一化后的单词（小写）

        Returns:
            可被 DictionaryResult.parse() 消费的字典
        """
        # 先查缓存（L1，内存，无 IO）
        cached = cache_get(word)
        if cached is not None:
            dict_result = DictionaryResult.model_validate(cached)
            dict_result.cached = True
            return dict_result.model_dump()

        # 查 PostgreSQL
        entry, lemma = await full_lookup(word)
        if entry is None:
            raise ValueError(f"Word not found: {word}")

        # 构建结果并缓存
        result: dict[str, Any] = self._build_result(word, entry, lemma)
        cache_set(word, result)
        return result

    def _build_result(
        self, query: str, entry: EntryRow, lemma: str | None
    ) -> dict[str, Any]:
        """
        将 EntryRow 构建为 DictionaryResult 字典。

        Args:
            query: 原始查询词
            entry: 数据库词条
            lemma: lemma 回退获取的原形（如果有）

        Returns:
            DictionaryResult 字典
        """
        # 解析 tags
        tags = self._parse_tags(entry.tag)

        # 解析 exchange
        exchange = self._parse_exchange(entry.exchange)

        # 解析 translation 为 meanings
        meanings = self._build_meanings(entry)

        # 构建 short_meaning
        short_meaning = None
        if entry.translation:
            # 取前50字符，避免过长
            short_meaning = (
                entry.translation[:50]
                if len(entry.translation) > 50
                else entry.translation
            )

        # 构建 EcdictEntry
        ecdict_entry = EcdictEntry(
            word=entry.word,
            lemma=lemma,
            phonetic=entry.phonetic,
            short_meaning=short_meaning,
            meanings=meanings,
            tags=tags,
            exchange=exchange,
        )

        # 构建完整 DictionaryResult
        return DictionaryResult(
            word=query,
            phonetic=entry.phonetic,
            audio_url=None,  # ECDICT 无音频
            meanings=meanings,
            cached=False,
            provider="ecdict_local",
            entry=ecdict_entry,
        ).model_dump()

    def _build_meanings(self, entry: EntryRow) -> list[DictionaryMeaning]:
        """将 entry 构建为 meanings 列表"""
        if not entry.translation:
            return []

        # translation 字段可能包含多个释义，用分号或换行分隔
        # ECDICT translation 格式: "发现; 找到; 发觉"
        translations = re.split(r"[；;|\n]", entry.translation)
        translations = [t.strip() for t in translations if t.strip()]

        if not translations:
            return []

        # 使用 pos 作为词性，如果没有则默认为 'n.'
        part_of_speech = entry.pos if entry.pos else "n."

        definitions = [
            DictionaryMeaningDefinition(meaning=t) for t in translations[:5]  # 最多5条
        ]

        return [
            DictionaryMeaning(
                part_of_speech=part_of_speech,
                definitions=definitions,
            )
        ]

    def _parse_tags(self, tag_str: str | None) -> list[str]:
        """解析 tag 字段为空格分隔的标签列表"""
        if not tag_str:
            return []
        # tag 字段格式: 'zk/中考 gk/高考 cet4/四级'
        # 转换为 ['CET4', '高考', '中考'] 等格式
        tags = []
        for t in tag_str.split():
            # 取 / 后面的中文标签，或直接用大写的英文标签
            if "/" in t:
                _, label = t.split("/", 1)
                tags.append(label)
            else:
                tags.append(t.upper())
        return tags

    def _parse_exchange(self, exchange_str: str | None) -> list[str]:
        """解析 exchange 字段为词形变换列表"""
        if not exchange_str:
            return []

        # 格式: 'p:perceived/d:perceived/3:perceives/i:perceiving'
        exchange = []
        for part in exchange_str.split("/"):
            if ":" in part:
                _, value = part.split(":", 1)
                exchange.append(value)
        return exchange

"""
PostgreSQL 版本的 ECDICT 查询实现。

使用 app.database.connection.DB_POOL 提供 async 查询能力。
字段名与 PostgreSQL schema 对齐：pos → part_of_speech。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.database.connection import DB_POOL


@dataclass(frozen=True)
class EntryRow:
    """词条数据行（PostgreSQL 版本）"""
    word: str
    phonetic: str | None
    definition: str | None
    translation: str | None
    pos: str | None  # PostgreSQL 列名
    tag: str | None
    exchange: str | None
    bnc: int | None
    frq: int | None

    # 别名，保持向后兼容
    @property
    def part_of_speech(self) -> str | None:
        return self.pos


def _row_to_entry(row: Any) -> EntryRow | None:
    """将 asyncpg.Row 转换为 EntryRow 或 None"""
    if row is None:
        return None
    return EntryRow(
        word=row["word"],
        phonetic=row["phonetic"],
        definition=row["definition"],
        translation=row["translation"],
        pos=row["part_of_speech"],  # PostgreSQL 列名
        tag=row["tag"],
        exchange=row["exchange"],
        bnc=row["bnc"],
        frq=row["frq"],
    )


async def exact_lookup(word: str) -> EntryRow | None:
    """
    精确查询词条。

    Args:
        word: 归一化后的单词（小写）

    Returns:
        EntryRow 或 None（未找到）
    """
    if DB_POOL is None:
        return None
    async with DB_POOL.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM ecdict_entries WHERE LOWER(word) = LOWER($1)",
            word,
        )
        return _row_to_entry(row)


async def lemma_lookup(word: str) -> tuple[EntryRow | None, str | None]:
    """
    Lemma 回退查询。

    1. 先查 ecdict_lemmas 表获取 word 的 lemma（原形）
    2. 再查 ecdict_entries 表获取 lemma 对应的词条

    Args:
        word: 归一化后的单词（小写）

    Returns:
        (EntryRow, lemma) 或 (None, None)（未找到）
    """
    if DB_POOL is None:
        return None, None
    async with DB_POOL.acquire() as conn:
        lemma_row = await conn.fetchrow(
            "SELECT lemma FROM ecdict_lemmas WHERE LOWER(inflected_form) = LOWER($1)",
            word,
        )
        if lemma_row is None:
            return None, None

        lemma = lemma_row["lemma"]

        entry_row = await conn.fetchrow(
            "SELECT * FROM ecdict_entries WHERE LOWER(word) = LOWER($1)",
            lemma,
        )
        return _row_to_entry(entry_row), lemma


async def full_lookup(word: str) -> tuple[EntryRow | None, str | None]:
    """
    完整查询：先精确匹配，失败则走 lemma 回退。

    Args:
        word: 归一化后的单词（小写）

    Returns:
        (EntryRow, lemma_or_none)
        - 精确匹配成功: (EntryRow, None)
        - lemma 回退成功: (EntryRow, lemma)
        - 都失败: (None, None)
    """
    entry = await exact_lookup(word)
    if entry is not None:
        return entry, None
    return await lemma_lookup(word)

#!/usr/bin/env python3
"""
ECDICT CSV 导入脚本（PostgreSQL 版本）

将 ECDICT CSV 数据导入 PostgreSQL 数据库。

用法:
    cd server
    python scripts/import_ecdict.py --csv /path/to/ecdict.csv

ECDICT 下载地址: https://github.com/skywind3000/ECDICT
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

import asyncpg


def _build_lemmas_from_exchange(word: str, exchange_str: str) -> list[tuple[str, str, str | None]]:
    """
    从 exchange 字段提取 lemma 词形列表。

    格式: 'p:perceived/d:perceived/3:perceives/i:perceiving'
    返回: [(inflected_form, lemma, rule), ...]
    rule 目前置为 None（rule 字段在 schema 中可空，后续可增强解析）
    """
    if not exchange_str:
        return []

    lemmas = []
    for part in exchange_str.split("/"):
        if ":" in part:
            key, value = part.split(":", 1)
            if key != "0":  # 跳过原型 (key='0')
                lemmas.append((value.lower(), word, None))
    return lemmas


async def _import_csv(csv_path: str, database_url: str, batch_size: int = 1000) -> tuple[int, int]:
    """
    导入 ECDICT CSV 文件到 PostgreSQL。

    Args:
        csv_path: CSV 文件路径
        database_url: PostgreSQL DSN
        batch_size: 每批提交数量

    Returns:
        (entries_count, lemmas_count): 插入的词条数和 lemma 数
    """
    pool = await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=batch_size,
        server_settings={"application_name": "ecdict_import"},
    )

    entries_count = 0
    lemmas_count = 0

    async with pool.acquire() as conn:
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            batch_entries: list[tuple] = []
            batch_lemmas: list[tuple] = []

            for row in reader:
                raw_word = row.get("word", "").strip()
                if not raw_word:
                    continue

                # ECDICT CSV 用单引号包裹以 - 或 ' 开头的词（如 "'hood", "'-ability"）
                # 只在首尾都有单引号时才剥离（保留词内正常的撇号如 "baker's"）
                if raw_word.startswith("'") and raw_word.endswith("'") and len(raw_word) > 1:
                    word = raw_word[1:-1].lower()
                else:
                    word = raw_word.lower()
                if not word:
                    continue

                exchange_str = row.get("exchange", "") or ""
                bnc_val = row.get("bnc", "") or ""
                frq_val = row.get("frq", "") or ""
                collins_val = row.get("collins", "") or ""
                oxford_val = row.get("oxford", "") or ""
                detail_val = row.get("detail", "") or ""

                # ecdict_entries 表字段（按 schema 列顺序）
                # Schema: word, phonetic, definition, translation, part_of_speech,
                #          exchange, tag, bnc, frq, oxford, collins, detail_json
                batch_entries.append((
                    word,                                    # $1 word
                    row.get("phonetic") or None,            # $2 phonetic
                    row.get("definition") or None,           # $3 definition
                    row.get("translation") or None,         # $4 translation
                    row.get("pos") or None,                # $5 part_of_speech
                    exchange_str or None,                   # $6 exchange
                    row.get("tag") or None,                # $7 tag
                    int(bnc_val) if bnc_val.isdigit() else None,   # $8 bnc
                    int(frq_val) if frq_val.isdigit() else None,    # $9 frq
                    int(oxford_val) if oxford_val.isdigit() else None,  # $10 oxford
                    int(collins_val) if collins_val.isdigit() else None,  # $11 collins
                    detail_val if detail_val else "{}",  # $12 detail_json (JSONB)
                ))

                # ecdict_lemmas 表
                for variant, lemma, rule in _build_lemmas_from_exchange(word, exchange_str):
                    batch_lemmas.append((variant, lemma, rule))
                    lemmas_count += 1

                # 批量提交
                if len(batch_entries) >= batch_size:
                    await _insert_batch(conn, batch_entries, batch_lemmas)
                    entries_count += len(batch_entries)
                    batch_entries = []
                    batch_lemmas = []
                    print(f"  已导入 {entries_count} 条词条...", file=sys.stderr)

            # 提交剩余数据
            if batch_entries:
                await _insert_batch(conn, batch_entries, batch_lemmas)
                entries_count += len(batch_entries)

    await pool.close()
    return entries_count, lemmas_count


async def _insert_batch(
    conn: asyncpg.Connection,
    entries: list[tuple],
    lemmas: list[tuple],
) -> None:
    """批量插入词条和 lemma"""
    # 插入 ecdict_entries（INSERT ... ON CONFLICT DO NOTHING 防止重复）
    # 列顺序: word, phonetic, definition, translation, part_of_speech,
    #         exchange, tag, bnc, frq, oxford, collins, detail_json
    await conn.executemany(
        """
        INSERT INTO ecdict_entries
            (word, phonetic, definition, translation, part_of_speech,
             exchange, tag, bnc, frq, oxford, collins, detail_json)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ON CONFLICT (word) DO NOTHING
        """,
        entries,
    )

    # 插入 ecdict_lemmas
    if lemmas:
        await conn.executemany(
            """
            INSERT INTO ecdict_lemmas (inflected_form, lemma, rule)
            VALUES ($1, $2, $3)
            ON CONFLICT (inflected_form) DO NOTHING
            """,
            lemmas,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 ECDICT CSV 到 PostgreSQL")
    parser.add_argument(
        "--csv",
        required=True,
        help="ECDICT CSV 文件路径",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="每批插入数量 (默认: 1000)",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL DSN（默认从 DATABASE_URL 环境变量读取）",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"错误: 文件不存在: {csv_path}", file=sys.stderr)
        sys.exit(1)

    database_url = args.database_url
    if not database_url:
        print("错误: 未提供 --database-url 或 DATABASE_URL 环境变量", file=sys.stderr)
        sys.exit(1)

    print(f"开始导入 ECDICT CSV: {csv_path}")
    print(f"批次大小: {args.batch_size}")
    print(f"目标数据库: {database_url.split('@')[0]}@...")  # 不打印密码

    entries_count, lemmas_count = asyncio.run(
        _import_csv(str(csv_path), database_url, args.batch_size)
    )
    print("导入完成!")
    print(f"  词条数: {entries_count}")
    print(f"  Lemma 数: {lemmas_count}")


if __name__ == "__main__":
    main()

"""词典数据管理工具的数据库操作服务。"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from app.database import connection as db_connection

from .schemas import (
    DashboardStats,
    DataQualityIssue,
    DataQualityReport,
    DictionaryEntryDetail,
    DictionaryEntrySummary,
    EntryKind,
    LookupTargetRow,
    MeaningGroup,
    OperationLogEntry,
    PaginatedResult,
    RedirectRow,
    json_to_examples,
    json_to_meanings,
    json_to_phrases,
)

SOURCE = "tecd3"


class DictManagerService:
    """词典数据管理服务类。"""

    @staticmethod
    def _normalize_query(word: str) -> str:
        """归一化查询词。"""
        normalized = word.strip().lower()
        normalized = re.sub(r"^[^\w]+|[^\w]+$", "", normalized)
        return normalized

    @staticmethod
    def _build_preview_from_meanings(meanings: list[dict[str, Any]]) -> str | None:
        """从 meanings 构建预览文本。"""
        if not meanings:
            return None
        preview_parts: list[str] = []
        for group in meanings[:2]:
            definitions = group.get("definitions", [])
            for definition in definitions[:2]:
                meaning = str(definition.get("meaning") or "").strip()
                if meaning:
                    preview_parts.append(meaning)
        preview = "；".join(preview_parts)
        return preview[:180] if preview else None

    @staticmethod
    def _get_first_pos(meanings: list[dict[str, Any]]) -> str | None:
        """获取第一个词性。"""
        for group in meanings:
            pos = str(group.get("part_of_speech") or "").strip()
            if pos:
                return pos
        return None

    async def log_operation(
        self,
        operation: str,
        table_name: str,
        entry_id: int | None = None,
        record_id: int | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        note: str | None = None,
    ) -> int:
        """记录操作日志。"""
        if db_connection.DB_POOL is None:
            return 0
        async with db_connection.DB_POOL.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO dict_operation_logs (
                    entry_id, operation, table_name, record_id, old_value, new_value, note
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7)
                RETURNING id
                """,
                entry_id,
                operation,
                table_name,
                record_id,
                json.dumps(old_value, ensure_ascii=False) if old_value else None,
                json.dumps(new_value, ensure_ascii=False) if new_value else None,
                note,
            )
            return row["id"] if row else 0

    async def get_dashboard_stats(self) -> DashboardStats:
        """获取仪表盘统计数据。"""
        if db_connection.DB_POOL is None:
            return DashboardStats(
                total_entries=0,
                total_fragments=0,
                entries_with_meanings=0,
                entries_without_meanings=0,
                total_lookup_targets=0,
                total_redirects=0,
                entries_without_lookup_targets=0,
                duplicate_lookup_keys=0,
                orphan_redirects=0,
            )

        async with db_connection.DB_POOL.acquire() as conn:
            total_entries = await conn.fetchval(
                "SELECT COUNT(*) FROM dict_entries WHERE entry_kind = 'entry' AND source = $1", SOURCE
            )
            total_fragments = await conn.fetchval(
                "SELECT COUNT(*) FROM dict_entries WHERE entry_kind = 'fragment' AND source = $1", SOURCE
            )
            entries_with_meanings = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_entries
                WHERE source = $1 AND meanings_json IS NOT NULL AND meanings_json != '[]'::jsonb
                """,
                SOURCE,
            )
            total_lookup_targets = await conn.fetchval(
                "SELECT COUNT(*) FROM dict_lookup_targets WHERE source = $1", SOURCE
            )
            total_redirects = await conn.fetchval(
                "SELECT COUNT(*) FROM dict_redirects WHERE source = $1", SOURCE
            )
            entries_without_lookup_targets = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_entries e
                WHERE e.source = $1 AND NOT EXISTS (
                    SELECT 1 FROM dict_lookup_targets t WHERE t.entry_id = e.id AND t.source = e.source
                )
                """,
                SOURCE,
            )
            duplicate_lookup_keys = await conn.fetchval(
                """
                SELECT COUNT(*) FROM (
                    SELECT normalized_form, entry_id, match_kind
                    FROM dict_lookup_targets WHERE source = $1
                    GROUP BY normalized_form, entry_id, match_kind
                    HAVING COUNT(*) > 1
                ) duplicates
                """,
                SOURCE,
            )
            orphan_redirects = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_redirects r
                WHERE r.source = $1 AND NOT EXISTS (
                    SELECT 1 FROM dict_entries e
                    WHERE e.source = r.source AND e.source_entry_key = r.target_entry_key
                )
                """,
                SOURCE,
            )

            return DashboardStats(
                total_entries=total_entries or 0,
                total_fragments=total_fragments or 0,
                entries_with_meanings=entries_with_meanings or 0,
                entries_without_meanings=(total_entries or 0) + (total_fragments or 0) - (entries_with_meanings or 0),
                total_lookup_targets=total_lookup_targets or 0,
                total_redirects=total_redirects or 0,
                entries_without_lookup_targets=entries_without_lookup_targets or 0,
                duplicate_lookup_keys=duplicate_lookup_keys or 0,
                orphan_redirects=orphan_redirects or 0,
            )

    async def get_entries_without_meanings(
        self, page: int = 1, page_size: int = 50
    ) -> PaginatedResult:
        """获取缺失 meanings_json 的词条列表。"""
        if db_connection.DB_POOL is None:
            return PaginatedResult(total=0, page=page, page_size=page_size, items=[])

        offset = (page - 1) * page_size

        async with db_connection.DB_POOL.acquire() as conn:
            total = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_entries
                WHERE source = $1 AND (meanings_json IS NULL OR meanings_json = '[]'::jsonb)
                """,
                SOURCE,
            )

            rows = await conn.fetch(
                """
                SELECT
                    id,
                    source_entry_key,
                    display_headword,
                    entry_kind,
                    phonetic,
                    meanings_json,
                    created_at,
                    updated_at
                FROM dict_entries
                WHERE source = $1 AND (meanings_json IS NULL OR meanings_json = '[]'::jsonb)
                ORDER BY id ASC
                LIMIT $2 OFFSET $3
                """,
                SOURCE,
                page_size,
                offset,
            )

            items = []
            for row in rows:
                meanings = json_to_meanings(row["meanings_json"])
                preview = self._build_preview_from_meanings(
                    [m.model_dump() for m in meanings]
                ) if meanings else None
                items.append({
                    "id": row["id"],
                    "source_entry_key": row["source_entry_key"],
                    "display_headword": row["display_headword"],
                    "entry_kind": row["entry_kind"],
                    "phonetic": row["phonetic"],
                    "has_meanings": len(meanings) > 0,
                    "preview": preview,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                })

            return PaginatedResult(
                total=total or 0,
                page=page,
                page_size=page_size,
                items=items,
            )

    async def search_entries(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 50,
        entry_kind: str | None = None,
        has_meanings: bool | None = None,
    ) -> PaginatedResult:
        """搜索词条。"""
        if db_connection.DB_POOL is None:
            return PaginatedResult(total=0, page=page, page_size=page_size, items=[])

        offset = (page - 1) * page_size

        conditions = ["source = $1"]
        params: list[Any] = [SOURCE]
        param_idx = 2

        if keyword:
            normalized = self._normalize_query(keyword)
            conditions.append(
                "(LOWER(display_headword) LIKE $%d OR LOWER(base_headword) LIKE $%d OR LOWER(source_entry_key) LIKE $%d)"
                % (param_idx, param_idx + 1, param_idx + 2)
            )
            params.append(f"%{normalized}%")
            params.append(f"%{normalized}%")
            params.append(f"%{normalized}%")
            param_idx += 3

        if entry_kind:
            conditions.append(f"entry_kind = ${param_idx}")
            params.append(entry_kind)
            param_idx += 1

        if has_meanings is True:
            conditions.append("(meanings_json IS NOT NULL AND meanings_json != '[]'::jsonb)")
        elif has_meanings is False:
            conditions.append("(meanings_json IS NULL OR meanings_json = '[]'::jsonb)")

        where_clause = " AND ".join(conditions)

        async with db_connection.DB_POOL.acquire() as conn:
            total = await conn.fetchval(
                f"SELECT COUNT(*) FROM dict_entries WHERE {where_clause}",
                *params,
            )

            rows = await conn.fetch(
                f"""
                SELECT
                    id,
                    source_entry_key,
                    display_headword,
                    entry_kind,
                    phonetic,
                    meanings_json,
                    created_at,
                    updated_at
                FROM dict_entries
                WHERE {where_clause}
                ORDER BY id ASC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """,
                *params,
                page_size,
                offset,
            )

            items = []
            for row in rows:
                meanings = json_to_meanings(row["meanings_json"])
                preview = self._build_preview_from_meanings(
                    [m.model_dump() for m in meanings]
                ) if meanings else None
                items.append({
                    "id": row["id"],
                    "source_entry_key": row["source_entry_key"],
                    "display_headword": row["display_headword"],
                    "entry_kind": row["entry_kind"],
                    "phonetic": row["phonetic"],
                    "has_meanings": len(meanings) > 0,
                    "preview": preview,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                })

            return PaginatedResult(
                total=total or 0,
                page=page,
                page_size=page_size,
                items=items,
            )

    async def get_entry_detail(self, entry_id: int) -> DictionaryEntryDetail | None:
        """获取词条详情。"""
        if db_connection.DB_POOL is None:
            return None

        async with db_connection.DB_POOL.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM dict_entries WHERE id = $1 AND source = $2
                """,
                entry_id,
                SOURCE,
            )
            if not row:
                return None

            meanings = json_to_meanings(row["meanings_json"])
            examples = json_to_examples(row["examples_json"])
            phrases = json_to_phrases(row["phrases_json"])

            return DictionaryEntryDetail(
                id=row["id"],
                source=row["source"],
                source_entry_key=row["source_entry_key"],
                entry_kind=EntryKind(row["entry_kind"]),
                display_headword=row["display_headword"],
                base_headword=row["base_headword"],
                homograph_no=row["homograph_no"],
                phonetic=row["phonetic"],
                exam_tags=list(row["exam_tags"]) if row["exam_tags"] else [],
                parse_version=row["parse_version"] or "tecd3_v2",
                meanings=meanings,
                examples=examples,
                phrases=phrases,
                meanings_json_raw=json.dumps(row["meanings_json"], ensure_ascii=False, indent=2) if row["meanings_json"] else None,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def update_entry(
        self,
        entry_id: int,
        meanings: list[MeaningGroup],
        examples: list[dict[str, Any]] | None = None,
        phrases: list[dict[str, Any]] | None = None,
        phonetic: str | None = None,
        base_headword: str | None = None,
        homograph_no: int | None = None,
        entry_kind: str | None = None,
        update_note: str | None = None,
    ) -> bool:
        """更新词条，记录操作日志并维护关联表。"""
        if db_connection.DB_POOL is None:
            return False

        async with db_connection.DB_POOL.acquire() as conn:
            old_row = await conn.fetchrow(
                """
                SELECT * FROM dict_entries WHERE id = $1 AND source = $2
                """,
                entry_id,
                SOURCE,
            )
            if not old_row:
                return False

            old_value = {
                "meanings_json": old_row["meanings_json"],
                "examples_json": old_row["examples_json"],
                "phrases_json": old_row["phrases_json"],
                "phonetic": old_row["phonetic"],
                "base_headword": old_row["base_headword"],
                "homograph_no": old_row["homograph_no"],
                "entry_kind": old_row["entry_kind"],
            }

            meanings_dict = [m.model_dump() for m in meanings]
            examples_dict = examples or []
            phrases_dict = phrases or []

            new_base_headword = base_headword if base_headword is not None else old_row["base_headword"]
            new_phonetic = phonetic if phonetic is not None else old_row["phonetic"]
            new_homograph_no = homograph_no if homograph_no is not None else old_row["homograph_no"]
            new_entry_kind = entry_kind if entry_kind else old_row["entry_kind"]

            new_value = {
                "meanings_json": meanings_dict,
                "examples_json": examples_dict,
                "phrases_json": phrases_dict,
                "phonetic": new_phonetic,
                "base_headword": new_base_headword,
                "homograph_no": new_homograph_no,
                "entry_kind": new_entry_kind,
            }

            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE dict_entries SET
                        meanings_json = $1::jsonb,
                        examples_json = $2::jsonb,
                        phrases_json = $3::jsonb,
                        phonetic = $4,
                        base_headword = $5,
                        homograph_no = $6,
                        entry_kind = $7,
                        updated_at = NOW()
                    WHERE id = $8 AND source = $9
                    """,
                    json.dumps(meanings_dict, ensure_ascii=False),
                    json.dumps(examples_dict, ensure_ascii=False),
                    json.dumps(phrases_dict, ensure_ascii=False),
                    new_phonetic,
                    new_base_headword,
                    new_homograph_no,
                    new_entry_kind,
                    entry_id,
                    SOURCE,
                )

                preview = self._build_preview_from_meanings(meanings_dict)
                target_pos = self._get_first_pos(meanings_dict)

                existing_targets = await conn.fetch(
                    """
                    SELECT * FROM dict_lookup_targets
                    WHERE entry_id = $1 AND source = $2
                    ORDER BY id
                    """,
                    entry_id,
                    SOURCE,
                )

                for target in existing_targets:
                    should_update = False
                    update_fields = {}

                    if target.get("preview_text") != preview:
                        update_fields["preview_text"] = preview
                        should_update = True

                    if target.get("target_pos") != target_pos:
                        update_fields["target_pos"] = target_pos
                        should_update = True

                    if should_update:
                        set_clauses = []
                        update_params: list[Any] = []
                        param_idx = 1

                        for field, value in update_fields.items():
                            set_clauses.append(f"{field} = ${param_idx}")
                            update_params.append(value)
                            param_idx += 1

                        update_params.extend([target["id"], SOURCE])

                        await conn.execute(
                            f"UPDATE dict_lookup_targets SET {', '.join(set_clauses)} WHERE id = ${param_idx - 1} AND source = ${param_idx}",
                            *update_params,
                        )

                await self.log_operation(
                    operation="update",
                    table_name="dict_entries",
                    entry_id=entry_id,
                    record_id=entry_id,
                    old_value=old_value,
                    new_value=new_value,
                    note=update_note or "更新词条内容",
                )

            return True

    async def get_entry_lookup_targets(self, entry_id: int) -> list[LookupTargetRow]:
        """获取词条的查询目标关联记录。"""
        if db_connection.DB_POOL is None:
            return []

        async with db_connection.DB_POOL.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM dict_lookup_targets
                WHERE entry_id = $1 AND source = $2
                ORDER BY rank ASC, id ASC
                """,
                entry_id,
                SOURCE,
            )

            return [
                LookupTargetRow(
                    id=row["id"],
                    normalized_form=row["normalized_form"],
                    lookup_label=row["lookup_label"],
                    entry_id=row["entry_id"],
                    target_label=row["target_label"],
                    target_pos=row["target_pos"],
                    preview_text=row["preview_text"],
                    rank=row["rank"],
                    match_kind=row["match_kind"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    async def get_entry_redirects(self, entry_id: int) -> list[RedirectRow]:
        """获取指向该词条的重定向记录。"""
        if db_connection.DB_POOL is None:
            return []

        async with db_connection.DB_POOL.acquire() as conn:
            entry = await conn.fetchrow(
                "SELECT source_entry_key FROM dict_entries WHERE id = $1 AND source = $2",
                entry_id,
                SOURCE,
            )
            if not entry:
                return []

            rows = await conn.fetch(
                """
                SELECT * FROM dict_redirects
                WHERE source = $1 AND target_entry_key = $2
                ORDER BY id ASC
                """,
                SOURCE,
                entry["source_entry_key"],
            )

            return [
                RedirectRow(
                    id=row["id"],
                    redirect_key=row["redirect_key"],
                    target_entry_key=row["target_entry_key"],
                    redirect_kind=row["redirect_kind"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    async def add_lookup_target(
        self,
        entry_id: int,
        normalized_form: str,
        lookup_label: str,
        target_label: str,
        target_pos: str | None = None,
        preview_text: str | None = None,
        rank: int = 0,
        match_kind: str = "headword",
        update_note: str | None = None,
    ) -> int | None:
        """添加查询目标关联，记录日志。"""
        if db_connection.DB_POOL is None:
            return None

        async with db_connection.DB_POOL.acquire() as conn:
            entry = await conn.fetchrow(
                "SELECT display_headword, meanings_json FROM dict_entries WHERE id = $1 AND source = $2",
                entry_id,
                SOURCE,
            )
            if not entry:
                return None

            if preview_text is None:
                meanings = json_to_meanings(entry["meanings_json"])
                preview_text = self._build_preview_from_meanings([m.model_dump() for m in meanings])

            if target_pos is None:
                meanings = json_to_meanings(entry["meanings_json"])
                target_pos = self._get_first_pos([m.model_dump() for m in meanings])

            new_value = {
                "entry_id": entry_id,
                "normalized_form": normalized_form,
                "lookup_label": lookup_label,
                "target_label": target_label,
                "target_pos": target_pos,
                "preview_text": preview_text,
                "rank": rank,
                "match_kind": match_kind,
            }

            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO dict_lookup_targets (
                        source, normalized_form, lookup_label, entry_id,
                        target_label, target_pos, preview_text, rank, match_kind
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (source, normalized_form, entry_id, match_kind) DO UPDATE SET
                        lookup_label = EXCLUDED.lookup_label,
                        target_label = EXCLUDED.target_label,
                        target_pos = EXCLUDED.target_pos,
                        preview_text = EXCLUDED.preview_text,
                        rank = EXCLUDED.rank
                    RETURNING id
                    """,
                    SOURCE,
                    normalized_form,
                    lookup_label,
                    entry_id,
                    target_label,
                    target_pos,
                    preview_text,
                    rank,
                    match_kind,
                )

                if row:
                    await self.log_operation(
                        operation="insert",
                        table_name="dict_lookup_targets",
                        entry_id=entry_id,
                        record_id=row["id"],
                        old_value=None,
                        new_value=new_value,
                        note=update_note or "添加查询目标关联",
                    )
                    return row["id"]
                return None

    async def add_redirect(
        self,
        redirect_key: str,
        target_entry_key: str,
        redirect_kind: str = "normalized_alias",
        update_note: str | None = None,
    ) -> int | None:
        """添加重定向记录，记录日志。"""
        if db_connection.DB_POOL is None:
            return None

        async with db_connection.DB_POOL.acquire() as conn:
            entry = await conn.fetchrow(
                "SELECT id, display_headword FROM dict_entries WHERE source_entry_key = $1 AND source = $2",
                target_entry_key,
                SOURCE,
            )
            if not entry:
                return None

            new_value = {
                "redirect_key": redirect_key,
                "target_entry_key": target_entry_key,
                "redirect_kind": redirect_kind,
            }

            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    INSERT INTO dict_redirects (source, redirect_key, target_entry_key, redirect_kind)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (source, redirect_key, target_entry_key, redirect_kind) DO NOTHING
                    RETURNING id
                    """,
                    SOURCE,
                    redirect_key,
                    target_entry_key,
                    redirect_kind,
                )

                if row:
                    await self.log_operation(
                        operation="insert",
                        table_name="dict_redirects",
                        entry_id=entry["id"],
                        record_id=row["id"],
                        old_value=None,
                        new_value=new_value,
                        note=update_note or "添加重定向记录",
                    )
                    return row["id"]
                return None

    async def delete_lookup_target(self, target_id: int, update_note: str | None = None) -> bool:
        """删除查询目标关联（软删除通过日志记录）。"""
        if db_connection.DB_POOL is None:
            return False

        async with db_connection.DB_POOL.acquire() as conn:
            old_row = await conn.fetchrow(
                "SELECT * FROM dict_lookup_targets WHERE id = $1 AND source = $2",
                target_id,
                SOURCE,
            )
            if not old_row:
                return False

            old_value = dict(old_row)

            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM dict_lookup_targets WHERE id = $1 AND source = $2",
                    target_id,
                    SOURCE,
                )

                await self.log_operation(
                    operation="delete",
                    table_name="dict_lookup_targets",
                    entry_id=old_row["entry_id"],
                    record_id=target_id,
                    old_value=old_value,
                    new_value=None,
                    note=update_note or "删除查询目标关联",
                )

            return True

    async def delete_redirect(self, redirect_id: int, update_note: str | None = None) -> bool:
        """删除重定向记录。"""
        if db_connection.DB_POOL is None:
            return False

        async with db_connection.DB_POOL.acquire() as conn:
            old_row = await conn.fetchrow(
                "SELECT * FROM dict_redirects WHERE id = $1 AND source = $2",
                redirect_id,
                SOURCE,
            )
            if not old_row:
                return False

            old_value = dict(old_row)

            entry = await conn.fetchrow(
                "SELECT id FROM dict_entries WHERE source_entry_key = $1 AND source = $2",
                old_row["target_entry_key"],
                SOURCE,
            )
            entry_id = entry["id"] if entry else None

            async with conn.transaction():
                await conn.execute(
                    "DELETE FROM dict_redirects WHERE id = $1 AND source = $2",
                    redirect_id,
                    SOURCE,
                )

                await self.log_operation(
                    operation="delete",
                    table_name="dict_redirects",
                    entry_id=entry_id,
                    record_id=redirect_id,
                    old_value=old_value,
                    new_value=None,
                    note=update_note or "删除重定向记录",
                )

            return True

    async def get_operation_logs(
        self, entry_id: int | None = None, page: int = 1, page_size: int = 50
    ) -> PaginatedResult:
        """获取操作日志。"""
        if db_connection.DB_POOL is None:
            return PaginatedResult(total=0, page=page, page_size=page_size, items=[])

        offset = (page - 1) * page_size

        async with db_connection.DB_POOL.acquire() as conn:
            if entry_id:
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM dict_operation_logs WHERE entry_id = $1",
                    entry_id,
                )
                rows = await conn.fetch(
                    """
                    SELECT * FROM dict_operation_logs
                    WHERE entry_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    entry_id,
                    page_size,
                    offset,
                )
            else:
                total = await conn.fetchval("SELECT COUNT(*) FROM dict_operation_logs")
                rows = await conn.fetch(
                    """
                    SELECT * FROM dict_operation_logs
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    page_size,
                    offset,
                )

            items = [
                {
                    "id": row["id"],
                    "entry_id": row["entry_id"],
                    "operation": row["operation"],
                    "table_name": row["table_name"],
                    "record_id": row["record_id"],
                    "old_value": row["old_value"],
                    "new_value": row["new_value"],
                    "note": row["note"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]

            return PaginatedResult(
                total=total or 0,
                page=page,
                page_size=page_size,
                items=items,
            )

    async def check_data_quality(self) -> DataQualityReport:
        """检查数据质量问题。"""
        if db_connection.DB_POOL is None:
            return DataQualityReport(summary={}, issues=[])

        issues: list[DataQualityIssue] = []
        summary: dict[str, int] = {}

        async with db_connection.DB_POOL.acquire() as conn:
            entries_without_meanings = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_entries
                WHERE source = $1 AND (meanings_json IS NULL OR meanings_json = '[]'::jsonb)
                """,
                SOURCE,
            )
            if entries_without_meanings:
                sample = await conn.fetch(
                    """
                    SELECT id, display_headword, source_entry_key
                    FROM dict_entries
                    WHERE source = $1 AND (meanings_json IS NULL OR meanings_json = '[]'::jsonb)
                    ORDER BY id LIMIT 10
                    """,
                    SOURCE,
                )
                issues.append(
                    DataQualityIssue(
                        issue_type="缺失释义",
                        issue_code="missing_meanings",
                        severity="high",
                        count=entries_without_meanings,
                        sample_records=[dict(row) for row in sample],
                    )
                )
                summary["missing_meanings"] = entries_without_meanings

            entries_without_lookup = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_entries e
                WHERE e.source = $1 AND NOT EXISTS (
                    SELECT 1 FROM dict_lookup_targets t WHERE t.entry_id = e.id AND t.source = e.source
                )
                """,
                SOURCE,
            )
            if entries_without_lookup:
                sample = await conn.fetch(
                    """
                    SELECT e.id, e.display_headword, e.source_entry_key
                    FROM dict_entries e
                    WHERE e.source = $1 AND NOT EXISTS (
                        SELECT 1 FROM dict_lookup_targets t WHERE t.entry_id = e.id AND t.source = e.source
                    )
                    ORDER BY e.id LIMIT 10
                    """,
                    SOURCE,
                )
                issues.append(
                    DataQualityIssue(
                        issue_type="孤立词条",
                        issue_code="orphan_entries",
                        severity="high",
                        count=entries_without_lookup,
                        sample_records=[dict(row) for row in sample],
                    )
                )
                summary["orphan_entries"] = entries_without_lookup

            orphan_redirects = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_redirects r
                WHERE r.source = $1 AND NOT EXISTS (
                    SELECT 1 FROM dict_entries e
                    WHERE e.source = r.source AND e.source_entry_key = r.target_entry_key
                )
                """,
                SOURCE,
            )
            if orphan_redirects:
                sample = await conn.fetch(
                    """
                    SELECT r.id, r.redirect_key, r.target_entry_key
                    FROM dict_redirects r
                    WHERE r.source = $1 AND NOT EXISTS (
                        SELECT 1 FROM dict_entries e
                        WHERE e.source = r.source AND e.source_entry_key = r.target_entry_key
                    )
                    ORDER BY r.id LIMIT 10
                    """,
                    SOURCE,
                )
                issues.append(
                    DataQualityIssue(
                        issue_type="孤立重定向",
                        issue_code="orphan_redirects",
                        severity="medium",
                        count=orphan_redirects,
                        sample_records=[dict(row) for row in sample],
                    )
                )
                summary["orphan_redirects"] = orphan_redirects

            duplicate_lookups = await conn.fetchval(
                """
                SELECT COUNT(*) FROM (
                    SELECT normalized_form, entry_id, match_kind
                    FROM dict_lookup_targets WHERE source = $1
                    GROUP BY normalized_form, entry_id, match_kind
                    HAVING COUNT(*) > 1
                ) duplicates
                """,
                SOURCE,
            )
            if duplicate_lookups:
                sample = await conn.fetch(
                    """
                    SELECT normalized_form, entry_id, match_kind, COUNT(*) as cnt
                    FROM dict_lookup_targets WHERE source = $1
                    GROUP BY normalized_form, entry_id, match_kind
                    HAVING COUNT(*) > 1
                    ORDER BY cnt DESC LIMIT 10
                    """,
                    SOURCE,
                )
                issues.append(
                    DataQualityIssue(
                        issue_type="重复查询目标",
                        issue_code="duplicate_lookups",
                        severity="medium",
                        count=duplicate_lookups,
                        sample_records=[dict(row) for row in sample],
                    )
                )
                summary["duplicate_lookups"] = duplicate_lookups

            invalid_json = await conn.fetchval(
                """
                SELECT COUNT(*) FROM dict_entries
                WHERE source = $1 AND (
                    jsonb_typeof(meanings_json) IS NULL
                    OR jsonb_typeof(examples_json) IS NULL
                    OR jsonb_typeof(phrases_json) IS NULL
                )
                """,
                SOURCE,
            )
            if invalid_json:
                sample = await conn.fetch(
                    """
                    SELECT id, display_headword, source_entry_key
                    FROM dict_entries
                    WHERE source = $1 AND (
                        jsonb_typeof(meanings_json) IS NULL
                        OR jsonb_typeof(examples_json) IS NULL
                        OR jsonb_typeof(phrases_json) IS NULL
                    )
                    ORDER BY id LIMIT 10
                    """,
                    SOURCE,
                )
                issues.append(
                    DataQualityIssue(
                        issue_type="无效JSON",
                        issue_code="invalid_json",
                        severity="high",
                        count=invalid_json,
                        sample_records=[dict(row) for row in sample],
                    )
                )
                summary["invalid_json"] = invalid_json

        return DataQualityReport(summary=summary, issues=issues)

    async def ensure_operation_log_table(self) -> None:
        """确保操作日志表存在。"""
        if db_connection.DB_POOL is None:
            return

        async with db_connection.DB_POOL.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dict_operation_logs (
                    id BIGSERIAL PRIMARY KEY,
                    entry_id BIGINT REFERENCES dict_entries(id) ON DELETE SET NULL,
                    operation TEXT NOT NULL CHECK (operation IN ('insert', 'update', 'delete')),
                    table_name TEXT NOT NULL,
                    record_id BIGINT,
                    old_value JSONB,
                    new_value JSONB,
                    note TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dict_operation_logs_entry_id ON dict_operation_logs(entry_id)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dict_operation_logs_created_at ON dict_operation_logs(created_at DESC)"
            )

"""
Analysis Records Service.

Handles CRUD operations for analysis_records table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.database import connection as db_connection


async def upsert_record(
    user_id: UUID,
    client_record_id: str,
    source_type: str,
    title: str | None,
    source_text: str,
    source_text_hash: str,
    request_payload_json: dict[str, Any],
    render_scene_json: dict[str, Any],
    page_state_json: dict[str, Any],
    reading_goal: str | None,
    reading_variant: str | None,
    user_facing_state: str | None,
    workflow_version: str | None,
    schema_version: str | None,
    analysis_status: str,
) -> tuple[UUID, bool, datetime]:
    """
    Upsert an analysis record.

    Returns:
        (id, created, updated_at)
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        now = datetime.now(timezone.utc)
        row = await conn.fetchrow(
            """
            INSERT INTO analysis_records (
                user_id, client_record_id, source_type, title, source_text,
                source_text_hash, request_payload_json, render_scene_json,
                page_state_json, reading_goal, reading_variant, user_facing_state,
                workflow_version, schema_version, analysis_status, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $16)
            ON CONFLICT (user_id, client_record_id) DO UPDATE SET
                title            = EXCLUDED.title,
                source_text      = EXCLUDED.source_text,
                source_text_hash = EXCLUDED.source_text_hash,
                request_payload_json = EXCLUDED.request_payload_json,
                render_scene_json   = EXCLUDED.render_scene_json,
                page_state_json     = EXCLUDED.page_state_json,
                reading_goal        = EXCLUDED.reading_goal,
                reading_variant     = EXCLUDED.reading_variant,
                user_facing_state   = EXCLUDED.user_facing_state,
                workflow_version    = EXCLUDED.workflow_version,
                schema_version      = EXCLUDED.schema_version,
                analysis_status     = EXCLUDED.analysis_status,
                updated_at          = $16
            WHERE analysis_records.user_id = $1
            RETURNING id, updated_at,
                (xmax = 0) AS created
            """,
            user_id,
            client_record_id,
            source_type,
            title,
            source_text,
            source_text_hash,
            request_payload_json,
            render_scene_json,
            page_state_json,
            reading_goal,
            reading_variant,
            user_facing_state,
            workflow_version,
            schema_version,
            analysis_status,
            now,
        )
        assert row is not None
        return UUID(str(row["id"])), bool(row["created"]), row["updated_at"]


async def get_record_by_id(
    user_id: UUID,
    record_id: UUID,
) -> dict | None:
    """Get a single record by id, ensuring it belongs to user."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, client_record_id, source_type, title, source_text,
                   source_text_hash, request_payload_json, render_scene_json,
                   page_state_json, reading_goal, reading_variant, user_facing_state,
                   workflow_version, schema_version, analysis_status,
                   last_opened_at, created_at, updated_at
            FROM analysis_records
            WHERE id = $1 AND user_id = $2
            """,
            record_id,
            user_id,
        )
        if row is None:
            return None
        return dict(row)


async def list_records(
    user_id: UUID,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """
    List records for a user with pagination.

    Returns:
        (items, total_count)
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    offset = (page - 1) * limit

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, client_record_id, source_type, title, source_text,
                   source_text_hash, request_payload_json, render_scene_json,
                   page_state_json, reading_goal, reading_variant, user_facing_state,
                   workflow_version, schema_version, analysis_status,
                   last_opened_at, created_at, updated_at
            FROM analysis_records
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id,
            limit,
            offset,
        )
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM analysis_records WHERE user_id = $1",
            user_id,
        )
        return [dict(row) for row in rows], int(total)


async def update_record(
    user_id: UUID,
    record_id: UUID,
    **fields: Any,
) -> dict | None:
    """Partial update. Returns updated record or None if not found."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    allowed = {
        "title", "render_scene_json", "page_state_json", "user_facing_state",
        "analysis_status", "last_opened_at",
    }
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return await get_record_by_id(user_id, record_id)

    updates["updated_at"] = datetime.now(timezone.utc)

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values()) + [record_id, user_id]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE analysis_records
            SET {set_clause}
            WHERE id = ${len(values)} AND user_id = ${len(values) + 1}
            RETURNING id, user_id, client_record_id, source_type, title, source_text,
                      source_text_hash, request_payload_json, render_scene_json,
                      page_state_json, reading_goal, reading_variant, user_facing_state,
                      workflow_version, schema_version, analysis_status,
                      last_opened_at, created_at, updated_at
            """,
            *values,
        )
        if row is None:
            return None
        return dict(row)


async def delete_record(user_id: UUID, record_id: UUID) -> bool:
    """Delete a record. Returns True if deleted."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM analysis_records
            WHERE id = $1 AND user_id = $2
            """,
            record_id,
            user_id,
        )
    return "DELETE 1" in result

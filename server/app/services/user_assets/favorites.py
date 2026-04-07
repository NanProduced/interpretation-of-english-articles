"""
Favorites Service.

Handles CRUD operations for favorite_records table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.database import connection as db_connection


async def add_favorite(
    user_id: UUID,
    target_type: str,
    target_key: str,
    analysis_record_id: UUID | None,
    payload_json: dict[str, Any],
    note: str | None,
) -> UUID:
    """
    Add a favorite (or no-op if already exists — uses ON CONFLICT DO NOTHING).

    Returns:
        id of the favorite record
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO favorite_records
                (user_id, target_type, target_key, analysis_record_id,
                 payload_json, note, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $7)
            ON CONFLICT (user_id, target_type, target_key) DO NOTHING
            RETURNING id
            """,
            user_id,
            target_type,
            target_key,
            analysis_record_id,
            payload_json,
            note,
            datetime.now(timezone.utc),
        )
        if row is not None:
            return UUID(str(row["id"]))

        # Already exists — fetch existing id
        existing = await conn.fetchrow(
            """
            SELECT id FROM favorite_records
            WHERE user_id = $1 AND target_type = $2 AND target_key = $3
            """,
            user_id,
            target_type,
            target_key,
        )
        assert existing is not None
        return UUID(str(existing["id"]))


async def list_favorites(
    user_id: UUID,
) -> list[dict]:
    """List all favorites for a user."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, user_id, target_type, target_key, analysis_record_id,
                   payload_json, note, created_at, updated_at
            FROM favorite_records
            WHERE user_id = $1
            ORDER BY created_at DESC
            """,
            user_id,
        )
        return [dict(row) for row in rows]


async def remove_favorite(
    user_id: UUID,
    target_type: str,
    target_key: str,
) -> bool:
    """Remove a favorite by target. Returns True if deleted."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM favorite_records
            WHERE user_id = $1 AND target_type = $2 AND target_key = $3
            """,
            user_id,
            target_type,
            target_key,
        )
    return "DELETE 1" in result


async def remove_favorite_by_analysis_record(
    user_id: UUID,
    analysis_record_id: UUID,
) -> int:
    """Remove favorites by analysis_record_id. Returns count deleted."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM favorite_records
            WHERE user_id = $1 AND analysis_record_id = $2
            """,
            user_id,
            analysis_record_id,
        )
        if "DELETE " in result:
            return int(result.split()[-1])
        return 0

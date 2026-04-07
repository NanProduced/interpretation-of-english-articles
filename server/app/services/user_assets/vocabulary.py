"""
Vocabulary Book Service.

Handles CRUD operations for vocabulary_book table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.database import connection as db_connection


async def upsert_vocabulary(
    user_id: UUID,
    lemma: str,
    display_word: str,
    short_meaning: str,
    analysis_record_id: UUID | None,
    phonetic: str | None,
    part_of_speech: str | None,
    meanings_json: list[dict[str, Any]],
    tags: list[str],
    exchange: list[str],
    source_provider: str,
    source_sentence: str | None,
    source_context: str | None,
    payload_json: dict[str, Any],
    mastery_status: str = "new",
) -> tuple[UUID, bool, datetime]:
    """
    Upsert a vocabulary entry (by user_id + lemma).

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
            INSERT INTO vocabulary_book (
                user_id, lemma, display_word, phonetic, part_of_speech,
                short_meaning, meanings_json, tags, exchange, source_provider,
                analysis_record_id, source_sentence, source_context,
                mastery_status, payload_json, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $16)
            ON CONFLICT (user_id, LOWER(lemma)) DO UPDATE SET
                display_word      = EXCLUDED.display_word,
                phonetic          = EXCLUDED.phonetic,
                part_of_speech    = EXCLUDED.part_of_speech,
                short_meaning     = EXCLUDED.short_meaning,
                meanings_json     = EXCLUDED.meanings_json,
                tags              = EXCLUDED.tags,
                exchange          = EXCLUDED.exchange,
                source_provider   = EXCLUDED.source_provider,
                analysis_record_id = EXCLUDED.analysis_record_id,
                source_sentence   = EXCLUDED.source_sentence,
                source_context     = EXCLUDED.source_context,
                payload_json      = EXCLUDED.payload_json,
                updated_at        = $16
            WHERE vocabulary_book.user_id = $1
            RETURNING id, updated_at,
                (xmax = 0) AS created
            """,
            user_id,
            lemma.lower(),
            display_word,
            phonetic,
            part_of_speech,
            short_meaning,
            meanings_json,
            tags,
            exchange,
            source_provider,
            analysis_record_id,
            source_sentence,
            source_context,
            mastery_status,
            payload_json,
            now,
        )
        assert row is not None
        return UUID(str(row["id"])), bool(row["created"]), row["updated_at"]


async def list_vocabulary(
    user_id: UUID,
    page: int = 1,
    limit: int = 50,
    mastery_status: str | None = None,
) -> tuple[list[dict], int]:
    """
    List vocabulary entries for a user with optional filtering.

    Returns:
        (items, total_count)
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    offset = (page - 1) * limit

    async with pool.acquire() as conn:
        if mastery_status:
            rows = await conn.fetch(
                """
                SELECT id, user_id, lemma, display_word, phonetic, part_of_speech,
                       short_meaning, meanings_json, tags, exchange, source_provider,
                       analysis_record_id, source_sentence, source_context,
                       mastery_status, review_count, last_reviewed_at,
                       payload_json, created_at, updated_at
                FROM vocabulary_book
                WHERE user_id = $1 AND mastery_status = $4
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
                mastery_status,
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM vocabulary_book WHERE user_id = $1 AND mastery_status = $2",
                user_id,
                mastery_status,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, user_id, lemma, display_word, phonetic, part_of_speech,
                       short_meaning, meanings_json, tags, exchange, source_provider,
                       analysis_record_id, source_sentence, source_context,
                       mastery_status, review_count, last_reviewed_at,
                       payload_json, created_at, updated_at
                FROM vocabulary_book
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset,
            )
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM vocabulary_book WHERE user_id = $1",
                user_id,
            )

        return [dict(row) for row in rows], int(total)


async def get_vocabulary_by_id(
    user_id: UUID,
    vocab_id: UUID,
) -> dict | None:
    """Get a single vocabulary entry by id."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, lemma, display_word, phonetic, part_of_speech,
                   short_meaning, meanings_json, tags, exchange, source_provider,
                   analysis_record_id, source_sentence, source_context,
                   mastery_status, review_count, last_reviewed_at,
                   payload_json, created_at, updated_at
            FROM vocabulary_book
            WHERE id = $1 AND user_id = $2
            """,
            vocab_id,
            user_id,
        )
        if row is None:
            return None
        return dict(row)


async def update_vocabulary(
    user_id: UUID,
    vocab_id: UUID,
    mastery_status: str | None,
    short_meaning: str | None,
    payload_json: dict[str, Any] | None,
) -> dict | None:
    """Partial update a vocabulary entry."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    now = datetime.now(timezone.utc)
    updates: dict[str, Any] = {"updated_at": now}
    if mastery_status is not None:
        updates["mastery_status"] = mastery_status
        updates["last_reviewed_at"] = now
    if short_meaning is not None:
        updates["short_meaning"] = short_meaning
    if payload_json is not None:
        updates["payload_json"] = payload_json

    if len(updates) == 1:  # only updated_at
        return await get_vocabulary_by_id(user_id, vocab_id)

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values()) + [vocab_id, user_id]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            UPDATE vocabulary_book
            SET {set_clause}
            WHERE id = ${len(values)} AND user_id = ${len(values) + 1}
            RETURNING id, user_id, lemma, display_word, phonetic, part_of_speech,
                      short_meaning, meanings_json, tags, exchange, source_provider,
                      analysis_record_id, source_sentence, source_context,
                      mastery_status, review_count, last_reviewed_at,
                      payload_json, created_at, updated_at
            """,
            *values,
        )
        if row is None:
            return None
        return dict(row)


async def delete_vocabulary(user_id: UUID, vocab_id: UUID) -> bool:
    """Delete a vocabulary entry. Returns True if deleted."""
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM vocabulary_book WHERE id = $1 AND user_id = $2",
            vocab_id,
            user_id,
        )
    return "DELETE 1" in result

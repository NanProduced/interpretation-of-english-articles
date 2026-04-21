"""
Vocabulary Book Service.

Handles CRUD operations for vocabulary_book table.
Upsert merges source_refs and collected_forms on conflict instead of overwriting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.database import connection as db_connection
from app.schemas.user_assets.vocabulary import VocabularyPayload

SOURCE_REFS_MAX = 20


def _merge_payload_on_conflict(
    existing_payload: dict[str, Any],
    incoming_payload: dict[str, Any],
    incoming_display_word: str,
) -> dict[str, Any]:
    """
    合并 payload_json：追加 source_refs 和 collected_forms，保留已有扩展字段。

    - source_refs: 追加 incoming 中的新条目，去重按 client_record_id + source_sentence_id，
      上限 SOURCE_REFS_MAX 条，超出时保留最近条目
    - collected_forms: 追加 incoming_display_word（去重）
    - audio_url: 保留已有值，不覆盖
    - 其他字段: 保留已有值
    """
    existing = (
        VocabularyPayload.model_validate(existing_payload)
        if existing_payload
        else VocabularyPayload()
    )
    incoming = (
        VocabularyPayload.model_validate(incoming_payload)
        if incoming_payload
        else VocabularyPayload()
    )

    existing_refs_map: dict[str, dict] = {}
    for ref in existing.source_refs:
        key = f"{ref.client_record_id}|{ref.source_sentence_id or ''}"
        existing_refs_map[key] = ref.model_dump(exclude_none=True)

    for ref in incoming.source_refs:
        key = f"{ref.client_record_id}|{ref.source_sentence_id or ''}"
        if key not in existing_refs_map:
            existing_refs_map[key] = ref.model_dump(exclude_none=True)

    all_refs = list(existing_refs_map.values())
    if len(all_refs) > SOURCE_REFS_MAX:
        all_refs = all_refs[-SOURCE_REFS_MAX:]

    seen_lower: dict[str, str] = {}
    for f in existing.collected_forms + incoming.collected_forms:
        low = f.lower()
        if low not in seen_lower:
            seen_lower[low] = f
    collected = list(seen_lower.values())
    if incoming_display_word and incoming_display_word.lower() not in seen_lower:
        collected.append(incoming_display_word)
        seen_lower[incoming_display_word.lower()] = incoming_display_word

    merged = existing.model_dump(exclude_none=True)
    merged["source_refs"] = all_refs
    merged["collected_forms"] = collected
    if incoming.audio_url and not existing.audio_url:
        merged["audio_url"] = incoming.audio_url

    return merged


async def upsert_vocabulary(
    user_id: UUID,
    lemma: str,
    display_word: str,
    short_meaning: str,
    dict_entry_id: int | None,
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

    On conflict (same user + lemma):
    - source_refs / collected_forms are MERGED (appended, not overwritten)
    - meanings_json / tags / exchange / short_meaning are updated to latest
    - source_sentence / source_context are updated to latest (most recent context)
    - dict_entry_id is updated if provided

    Returns:
        (id, created, updated_at)
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        async with conn.transaction():
            now = datetime.now(UTC)

            existing_row = await conn.fetchrow(
                """
                SELECT payload_json
                FROM vocabulary_book
                WHERE user_id = $1 AND LOWER(lemma) = LOWER($2)
                FOR UPDATE
                """,
                user_id,
                lemma,
            )

            if existing_row:
                existing_payload = (
                    dict(existing_row["payload_json"])
                    if existing_row["payload_json"]
                    else {}
                )
                merged_payload = _merge_payload_on_conflict(
                    existing_payload=existing_payload,
                    incoming_payload=payload_json,
                    incoming_display_word=display_word,
                )
            else:
                merged_payload = payload_json

            row = await conn.fetchrow(
                """
                INSERT INTO vocabulary_book (
                    user_id, lemma, display_word, phonetic, part_of_speech,
                    short_meaning, meanings_json, tags, exchange, source_provider,
                    dict_entry_id, source_sentence, source_context,
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
                    dict_entry_id     = COALESCE(EXCLUDED.dict_entry_id, vocabulary_book.dict_entry_id),
                    source_sentence   = EXCLUDED.source_sentence,
                    source_context    = EXCLUDED.source_context,
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
                json.dumps(meanings_json),
                tags,
                exchange,
                source_provider,
                dict_entry_id,
                source_sentence,
                source_context,
                mastery_status,
                json.dumps(merged_payload),
                now,
            )
            if row is None:
                raise RuntimeError("upsert_vocabulary failed: no row returned")
            return UUID(str(row["id"])), bool(row["created"]), row["updated_at"]


async def list_vocabulary(
    user_id: UUID,
    page: int = 1,
    limit: int = 50,
    mastery_status: str | None = None,
    lite: bool = False,
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
        fields = """
            v.id, v.user_id, v.lemma, v.display_word, v.phonetic, v.part_of_speech,
            v.short_meaning, v.tags, v.exchange, v.source_provider,
            v.dict_entry_id, v.mastery_status, v.review_count, v.last_reviewed_at,
            v.created_at, v.updated_at
        """
        if not lite:
            fields += ", v.meanings_json, v.source_sentence, v.source_context, v.payload_json"

        base_query = f"""
            SELECT {fields}
            FROM vocabulary_book v
            WHERE v.user_id = $1
        """
        if mastery_status:
            rows = await conn.fetch(
                base_query
                + " AND v.mastery_status = $4"
                + " ORDER BY v.created_at DESC LIMIT $2 OFFSET $3",
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
                base_query + " ORDER BY v.created_at DESC LIMIT $2 OFFSET $3",
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
            SELECT v.id, v.user_id, v.lemma, v.display_word, v.phonetic, v.part_of_speech,
                   v.short_meaning, v.meanings_json, v.tags, v.exchange, v.source_provider,
                   v.dict_entry_id, v.source_sentence, v.source_context,
                   v.mastery_status, v.review_count, v.last_reviewed_at,
                   v.payload_json, v.created_at, v.updated_at
            FROM vocabulary_book v
            WHERE v.id = $1 AND v.user_id = $2
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

    now = datetime.now(UTC)
    updates: dict[str, Any] = {"updated_at": now}
    if mastery_status is not None:
        updates["mastery_status"] = mastery_status
        updates["last_reviewed_at"] = now
    if short_meaning is not None:
        updates["short_meaning"] = short_meaning
    if payload_json is not None:
        updates["payload_json"] = json.dumps(payload_json)

    if len(updates) == 1:
        return await get_vocabulary_by_id(user_id, vocab_id)

    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    values = list(updates.values()) + [vocab_id, user_id]

    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            UPDATE vocabulary_book
            SET {set_clause}
            WHERE id = ${len(values)} AND user_id = ${len(values) + 1}
            """,
            *values,
        )
        return await get_vocabulary_by_id(user_id, vocab_id)


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


async def _load_user_vocab_lemmas(
    conn, user_id: UUID
) -> dict[str, dict[str, Any]]:
    """
    加载用户所有生词的 lemma → {vocab_id, lemma, mastery_status, collected_forms} 映射。

    返回的 dict key 为小写 lemma，value 包含原始字段。
    """
    rows = await conn.fetch(
        """
        SELECT id, lemma, mastery_status, payload_json
        FROM vocabulary_book
        WHERE user_id = $1
        """,
        user_id,
    )
    lemma_map: dict[str, dict[str, Any]] = {}
    for row in rows:
        payload = dict(row["payload_json"]) if row["payload_json"] else {}
        collected_forms: list[str] = payload.get("collected_forms", [])
        lemma_map[row["lemma"].lower()] = {
            "vocab_id": row["id"],
            "lemma": row["lemma"],
            "mastery_status": row["mastery_status"],
            "collected_forms": [f.lower() for f in collected_forms],
        }
    return lemma_map


def _match_tokens_against_vocab(
    sentences: list[dict],
    lemma_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    对句子 token 列表做生词匹配，返回匹配结果列表。

    匹配策略：
    1. 直接匹配：token 小写后直接在 lemma_map 中
    2. collected_forms 匹配：token 小写后出现在某词条的 collected_forms 中
    3. lemma candidates 匹配：通过 lemminflect 还原 token 后匹配 lemma
    """
    from app.services.dictionary.lemma import get_lemma_candidates

    matches: list[dict[str, Any]] = []

    for sent in sentences:
        sentence_id = sent["sentence_id"]
        tokens = sent["tokens"]

        occurrence_map: dict[str, int] = {}

        for token in tokens:
            cleaned = token.strip(".,;:!?\"'()[]{}").lower()
            if not cleaned:
                continue

            matched_entry = None

            if cleaned in lemma_map:
                matched_entry = lemma_map[cleaned]
            else:
                for entry in lemma_map.values():
                    if cleaned in entry["collected_forms"]:
                        matched_entry = entry
                        break

            if matched_entry is None:
                candidates = get_lemma_candidates(cleaned)
                for cand in candidates:
                    if cand.lower() in lemma_map:
                        matched_entry = lemma_map[cand.lower()]
                        break

            if matched_entry is None:
                continue

            lemma_key = matched_entry["lemma"].lower()
            occurrence_map[lemma_key] = occurrence_map.get(lemma_key, 0) + 1

            matches.append(
                {
                    "vocab_id": matched_entry["vocab_id"],
                    "lemma": matched_entry["lemma"],
                    "sentence_id": sentence_id,
                    "anchor_text": token,
                    "occurrence": occurrence_map[lemma_key],
                    "mastery_status": matched_entry["mastery_status"],
                }
            )

    return matches


async def find_vocab_highlights(
    user_id: UUID,
    sentences: list[dict],
) -> list[dict[str, Any]]:
    """
    查询句子列表中与用户生词本匹配的词条。

    Args:
        user_id: 用户 ID
        sentences: [{"sentence_id": str, "tokens": [str]}]

    Returns:
        匹配结果列表 [{"vocab_id", "lemma", "sentence_id", "anchor_text",
                       "occurrence", "mastery_status"}]
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        lemma_map = await _load_user_vocab_lemmas(conn, user_id)

    if not lemma_map:
        return []

    return _match_tokens_against_vocab(sentences, lemma_map)

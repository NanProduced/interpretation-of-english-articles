"""
Vocabulary Book API.

Provides endpoints for managing vocabulary entries.
"""

from __future__ import annotations

from logging import getLogger
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.user_assets.vocabulary import (
    VocabularyCreateRequest,
    VocabularyListResponse,
    VocabularyResponse,
    VocabularyUpdateRequest,
    VocabularyUpsertResponse,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.user_assets import vocabulary as vocab_svc

logger = getLogger("app.api")

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


def _vocab_row_to_response(row: dict) -> VocabularyResponse:
    return VocabularyResponse(
        id=row["id"],
        user_id=row["user_id"],
        lemma=row["lemma"],
        display_word=row["display_word"],
        phonetic=row.get("phonetic"),
        part_of_speech=row.get("part_of_speech"),
        short_meaning=row["short_meaning"],
        meanings_json=row.get("meanings_json"),
        tags=row.get("tags", []),
        exchange=row.get("exchange", []),
        source_provider=row.get("source_provider", "tecd3"),
        dict_entry_id=row.get("dict_entry_id"),
        source_sentence=row.get("source_sentence"),
        source_context=row.get("source_context"),
        mastery_status=row.get("mastery_status", "new"),
        review_count=row.get("review_count", 0),
        last_reviewed_at=row.get("last_reviewed_at"),
        payload_json=row.get("payload_json"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("", response_model=VocabularyUpsertResponse)
async def add_vocabulary(
    current_user: AuthUserDep,
    body: VocabularyCreateRequest,
) -> VocabularyUpsertResponse:
    """Add a word/phrase to vocabulary book (upsert by lemma)."""
    try:
        vocab_id, created, updated_at = await vocab_svc.upsert_vocabulary(
            user_id=UUID(current_user.user_id),
            lemma=body.lemma,
            display_word=body.display_word,
            short_meaning=body.short_meaning,
            dict_entry_id=body.dict_entry_id,
            phonetic=body.phonetic,
            part_of_speech=body.part_of_speech,
            meanings_json=body.meanings_json,
            tags=body.tags,
            exchange=body.exchange,
            source_provider=body.source_provider,
            source_sentence=body.source_sentence,
            source_context=body.source_context,
            payload_json=body.payload_json,
        )
        return VocabularyUpsertResponse(
            id=vocab_id,
            lemma=body.lemma,
            created=created,
            updated_at=updated_at,
        )
    except Exception as e:
        logger.error("add_vocabulary failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=VocabularyListResponse)
async def get_vocabulary_list(
    current_user: AuthUserDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    mastery_status: str | None = Query(default=None),
    lite: bool = Query(default=False, description="是否仅返回轻量字段用于列表展示"),
) -> VocabularyListResponse:
    """List vocabulary entries for the current user."""
    try:
        items, total = await vocab_svc.list_vocabulary(
            user_id=UUID(current_user.user_id),
            page=page,
            limit=limit,
            mastery_status=mastery_status,
            lite=lite,
        )
        return VocabularyListResponse(
            items=[_vocab_row_to_response(row) for row in items],
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error("list_vocabulary failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{vocab_id}", response_model=VocabularyResponse)
async def update_vocabulary(
    current_user: AuthUserDep,
    vocab_id: UUID,
    body: VocabularyUpdateRequest,
) -> VocabularyResponse:
    """Update a vocabulary entry (e.g., mastery status)."""
    try:
        updated = await vocab_svc.update_vocabulary(
            user_id=UUID(current_user.user_id),
            vocab_id=vocab_id,
            mastery_status=body.mastery_status,
            short_meaning=body.short_meaning,
            payload_json=body.payload_json,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="Vocabulary entry not found")
        return _vocab_row_to_response(updated)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("update_vocabulary failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{vocab_id}")
async def delete_vocabulary(
    current_user: AuthUserDep,
    vocab_id: UUID,
) -> dict:
    """Delete a vocabulary entry."""
    try:
        deleted = await vocab_svc.delete_vocabulary(
            user_id=UUID(current_user.user_id),
            vocab_id=vocab_id,
        )
        if not deleted:
            raise HTTPException(status_code=404, detail="Vocabulary entry not found")
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_vocabulary failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

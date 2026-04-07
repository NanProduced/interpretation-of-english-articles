"""
Vocabulary Book API.

Provides endpoints for managing vocabulary entries.
"""

from __future__ import annotations

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

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


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
            analysis_record_id=body.analysis_record_id,
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("", response_model=VocabularyListResponse)
async def list_vocabulary(
    current_user: AuthUserDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    mastery_status: str | None = Query(default=None),
) -> VocabularyListResponse:
    """List vocabulary entries for the current user."""
    try:
        items, total = await vocab_svc.list_vocabulary(
            user_id=UUID(current_user.user_id),
            page=page,
            limit=limit,
            mastery_status=mastery_status,
        )
        return VocabularyListResponse(
            items=[VocabularyResponse(**row) for row in items],
            total=total,
            page=page,
            limit=limit,
        )
    except Exception as e:
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
        return VocabularyResponse(**updated)
    except HTTPException:
        raise
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e)) from e

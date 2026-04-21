"""
Vocabulary Book API.

Provides endpoints for managing vocabulary entries.
"""

from __future__ import annotations

from logging import getLogger
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.user_assets.vocabulary import (
    DueVocabItem,
    DueVocabListResponse,
    ReviewStatsResponse,
    ReviewSubmitRequest,
    ReviewSubmitResponse,
    VocabHighlightsRequest,
    VocabHighlightsResponse,
    VocabMatchItem,
    VocabularyCreateRequest,
    VocabularyListResponse,
    VocabularyResponse,
    VocabularyUpdateRequest,
    VocabularyUpsertResponse,
)
from app.services.auth.dependencies import AuthUserDep
from app.services.user_assets import vocabulary as vocab_svc
from app.services.user_assets import review_system as review_svc

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
        next_review_at=row.get("next_review_at"),
        ease_factor=float(row.get("ease_factor", 2.5)),
        repetitions=row.get("repetitions", 0),
        review_interval=row.get("review_interval", 1),
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


@router.post("/highlights", response_model=VocabHighlightsResponse)
async def get_vocab_highlights(
    current_user: AuthUserDep,
    body: VocabHighlightsRequest,
) -> VocabHighlightsResponse:
    """查询句子列表中与用户生词本匹配的词条，用于结果页 overlay。"""
    try:
        sentences = [
            {"sentence_id": s.sentence_id, "tokens": s.tokens}
            for s in body.sentences
        ]
        matches = await vocab_svc.find_vocab_highlights(
            user_id=UUID(current_user.user_id),
            sentences=sentences,
        )
        return VocabHighlightsResponse(
            matches=[
                VocabMatchItem(
                    vocab_id=m["vocab_id"],
                    lemma=m["lemma"],
                    sentence_id=m["sentence_id"],
                    anchor_text=m["anchor_text"],
                    occurrence=m["occurrence"],
                    mastery_status=m["mastery_status"],
                )
                for m in matches
            ]
        )
    except Exception as e:
        logger.error("get_vocab_highlights failed: %s", e, exc_info=True)
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


# ---------------------------------------------------------------------------
# Review System Endpoints (艾宾浩斯遗忘曲线复习系统)
# ---------------------------------------------------------------------------


@router.get("/review-stats", response_model=ReviewStatsResponse)
async def get_review_stats(
    current_user: AuthUserDep,
) -> ReviewStatsResponse:
    """
    获取复习统计数据。

    返回用户生词本的复习统计，包括：
    - 总生词数
    - 今日待复习数
    - 逾期未复习数
    - 各掌握状态数量
    """
    try:
        stats = await review_svc.get_review_stats(
            user_id=UUID(current_user.user_id),
        )
        return ReviewStatsResponse(**stats)
    except Exception as e:
        logger.error("get_review_stats failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/due", response_model=DueVocabListResponse)
async def get_due_vocabulary(
    current_user: AuthUserDep,
    due_type: str = Query(default="today", description="待复习类型: today/overdue/new"),
    limit: int = Query(default=100, ge=1, le=500),
) -> DueVocabListResponse:
    """
    获取待复习单词列表。

    Args:
        due_type: 待复习类型
            - today: 今日待复习
            - overdue: 逾期未复习
            - new: 从未复习过的新词
        limit: 返回数量限制
    """
    try:
        items, total = await review_svc.get_due_vocabulary(
            user_id=UUID(current_user.user_id),
            due_type=due_type,
            limit=limit,
        )

        response_items: list[DueVocabItem] = []
        for row in items:
            response_items.append(
                DueVocabItem(
                    id=row["id"],
                    lemma=row["lemma"],
                    display_word=row["display_word"],
                    phonetic=row.get("phonetic"),
                    part_of_speech=row.get("part_of_speech"),
                    short_meaning=row["short_meaning"],
                    mastery_status=row["mastery_status"],
                    repetitions=row["repetitions"],
                    ease_factor=float(row["ease_factor"]),
                    review_interval=row["review_interval"],
                    next_review_at=row.get("next_review_at"),
                    source_sentence=row.get("source_sentence"),
                    source_refs=row.get("source_refs"),
                    meanings_json=row.get("meanings_json"),
                    payload_json=row.get("payload_json"),
                )
            )

        return DueVocabListResponse(
            items=response_items,
            total=total,
            due_type=due_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("get_due_vocabulary failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/review", response_model=ReviewSubmitResponse)
async def submit_review(
    current_user: AuthUserDep,
    body: ReviewSubmitRequest,
) -> ReviewSubmitResponse:
    """
    提交复习结果。

    根据 SM-2 算法（基于艾宾浩斯遗忘曲线）更新复习调度。

    Args:
        body: 包含 vocab_id 和 quality（0-5分）
            - 0: 完全忘记
            - 1: 几乎忘记
            - 2: 模糊记得
            - 3: 记住了
            - 4: 熟练掌握
            - 5: 完全掌握

    Returns:
        更新后的复习状态，包括下次复习时间和新的掌握状态
    """
    try:
        result = await review_svc.submit_review(
            user_id=UUID(current_user.user_id),
            vocab_id=body.vocab_id,
            quality=body.quality,
        )
        return ReviewSubmitResponse(
            vocab_id=result["vocab_id"],
            success=result["success"],
            next_review_at=result.get("next_review_at"),
            new_ease_factor=result["new_ease_factor"],
            new_interval=result["new_interval"],
            new_repetitions=result["new_repetitions"],
            new_mastery_status=result["new_mastery_status"],
            quality=result["quality"],
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("submit_review failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e

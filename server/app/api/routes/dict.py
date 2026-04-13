"""词典 Proxy API。"""

from __future__ import annotations

from logging import getLogger
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.services.dictionary import get_service
from app.services.dictionary.schemas import DictionaryEntryResult, DictionaryLookupResult
from app.services.dictionary.service import LookupError

logger = getLogger("app.api")

router = APIRouter(prefix="/dict", tags=["dict"])

_service = get_service()


@router.get("", response_model=DictionaryLookupResult)
async def lookup_word(
    q: str = Query(..., description="要查询的单词或短语", min_length=1, max_length=100),
    type: Literal["word", "phrase"] = Query(default="word", description="查询类型"),
    context_sentence: str | None = Query(default=None, description="点击词所在的句子"),
    occurrence: int | None = Query(default=None, description="在句子中的第几次出现"),
    reading_goal: str | None = Query(default=None, description="阅读目标"),
    reading_variant: str | None = Query(default=None, description="阅读变体"),
) -> DictionaryLookupResult:
    word = q.strip()
    from app.services.dictionary.schemas import DictionaryLookupRequest
    request = DictionaryLookupRequest(
        query=word,
        query_type=type,
        context_sentence=context_sentence,
        occurrence=occurrence,
        reading_goal=reading_goal,
        reading_variant=reading_variant,
    )
    try:
        return await _service.lookup(request)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Word not found: {word}") from None
    except Exception as exc:
        logger.error("lookup_word failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Dictionary service error: {exc}") from exc


@router.get("/entry", response_model=DictionaryEntryResult)
async def lookup_entry(
    id: int = Query(..., description="词条 ID", ge=1),
) -> DictionaryEntryResult:
    try:
        result = await _service.lookup_entry(id)
        return DictionaryEntryResult.model_validate(result)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Entry not found: {id}") from None
    except Exception as exc:
        logger.error("lookup_entry failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Dictionary service error: {exc}") from exc

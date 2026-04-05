"""
Dictionary Proxy API

提供词典查询代理服务，调用的第三方词典（可配置）。
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.dictionary import DictionaryService
from app.services.dictionary.schemas import (
    DictionaryMeaning,
    DictionaryMeaningDefinition,
    DictionaryResult,
)

router = APIRouter(prefix="/dict", tags=["dict"])


# === 向后兼容的请求/响应模型（与原接口一致）===

class DictionaryMeaningDefinition(BaseModel):
    """词典释义项"""
    meaning: str = Field(description="释义内容")
    example: str | None = Field(default=None, description="例句")
    example_translation: str | None = Field(default=None, description="例句中文翻译")


class DictionaryMeaning(BaseModel):
    """词典词性及释义"""
    part_of_speech: str = Field(description="词性，如 'n.', 'v.', 'adj.'")
    definitions: list[DictionaryMeaningDefinition] = Field(description="释义列表")


class DictionaryResult(BaseModel):
    """词典查询结果"""
    word: str = Field(description="查询的单词或短语")
    phonetic: str | None = Field(default=None, description="音标，如 '/fəˈnetɪk/'")
    audio_url: str | None = Field(default=None, description="发音音频 URL")
    meanings: list[DictionaryMeaning] = Field(default_factory=list, description="词性及释义列表")


# === 服务单例 ===
_service = DictionaryService()


# === 路由 ===

@router.get("", response_model=DictionaryResult)
async def lookup_word(
    q: str = Query(..., description="要查询的单词或短语", min_length=1, max_length=100),
    type: Literal["word", "phrase"] = Query(default="word", description="查询类型"),
) -> DictionaryResult:
    """
    查询词典释义

    - **q**: 要查询的单词或短语
    - **type**: word=单词查询, phrase=短语查询（暂不支持短语独立查询）
    """
    word = q.strip()
    try:
        result = _service.lookup(word)
        return DictionaryResult.model_validate(result.model_dump())
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Word not found: {word}")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Dictionary service error: {exc}") from exc

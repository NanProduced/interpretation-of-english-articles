"""
词典 Proxy API

提供词典查询代理服务。
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.dictionary import get_service
from app.services.dictionary.service import LookupError

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


class EcdictEntryResponse(BaseModel):
    """ECDICT 词条详情（MVP 扩展）"""
    word: str = Field(description="当前展示的单词")
    lemma: str | None = Field(default=None, description="词形还原后的原形")
    phonetic: str | None = Field(default=None, description="音标")
    short_meaning: str | None = Field(default=None, description="中文短释义")
    meanings: list[DictionaryMeaning] = Field(default_factory=list, description="词性及释义列表")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    exchange: list[str] = Field(default_factory=list, description="词形变换列表")


class DictionaryResult(BaseModel):
    """词典查询结果"""
    word: str = Field(description="查询的单词或短语")
    phonetic: str | None = Field(default=None, description="音标")
    audio_url: str | None = Field(default=None, description="发音音频 URL")
    meanings: list[DictionaryMeaning] = Field(default_factory=list, description="词性及释义列表")
    cached: bool = Field(default=False, description="是否来自缓存")
    provider: str = Field(default="ecdict_local", description="数据来源")
    entry: EcdictEntryResponse | None = Field(default=None, description="ECDICT 词条详情")


# === 路由 ===

_service = get_service()


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
        result = await _service.lookup(word)
        return DictionaryResult.model_validate(result)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Word not found: {word}") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Dictionary service error: {exc}") from exc

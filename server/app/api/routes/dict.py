"""
Dictionary Proxy API

提供词典查询代理服务，调用的第三方词典（可配置）。
"""

from __future__ import annotations

import os
from typing import Any, Literal, cast

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/dict", tags=["dict"])


# === 请求/响应模型 ===

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


# === 第三方词典配置 ===

# 默认使用 Free Dictionary API (https://dictionaryapi.dev/)
# 可通过环境变量 DICT_PROVIDER_URL 覆盖
DEFAULT_DICT_PROVIDER = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

DICT_PROVIDER_URL = os.getenv("DICT_PROVIDER_URL", DEFAULT_DICT_PROVIDER)


# === 简单HTTP客户端 ===

async def _fetch_word(word: str) -> list[dict[str, Any]]:
    """调用第三方词典 API"""
    url = DICT_PROVIDER_URL.format(word=word)
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Word not found: {word}")
        response.raise_for_status()
        return cast(list[dict[str, Any]], response.json())


def _parse_dict_api_response(word: str, data: list[dict[str, Any]]) -> DictionaryResult:
    """解析 Free Dictionary API 响应"""
    if not data:
        return DictionaryResult(word=word, meanings=[])

    # API 返回格式：[{word, phonetic?, phonetics?, meanings?, ...}]
    entry = data[0]

    # 提取音标
    phonetic = entry.get("phonetic")
    if not phonetic and entry.get("phonetics"):
        for p in entry["phonetics"]:
            if p.get("text"):
                phonetic = p.get("text")
                break

    # 提取音频 URL
    audio_url = None
    for p in entry.get("phonetics", []):
        if p.get("audio"):
            audio_url = p["audio"]
            break

    # 提取释义
    meanings: list[DictionaryMeaning] = []
    for m in entry.get("meanings", []):
        part_of_speech = m.get("partOfSpeech", "")
        defs: list[DictionaryMeaningDefinition] = []
        for d in m.get("definitions", []):
            defs.append(DictionaryMeaningDefinition(
                meaning=d.get("definition", ""),
                example=d.get("example"),
                example_translation=None,  # Free Dictionary API 不提供翻译
            ))
        meanings.append(DictionaryMeaning(
            part_of_speech=part_of_speech,
            definitions=defs,
        ))

    return DictionaryResult(
        word=word,
        phonetic=phonetic,
        audio_url=audio_url,
        meanings=meanings,
    )


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
    # 清理查询词
    word = q.strip()

    # 短语查询暂用单词查询（因为 Free Dictionary API 不支持短语）
    # 后续可扩展支持其他词典 API
    try:
        data = await _fetch_word(word)
        return _parse_dict_api_response(word, data)
    except HTTPException:
        # HTTPException 从 _fetch_word 直接传播
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Dictionary service error: {exc}") from exc

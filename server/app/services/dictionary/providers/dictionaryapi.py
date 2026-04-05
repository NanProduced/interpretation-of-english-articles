from __future__ import annotations

import os
from typing import Any, cast

import httpx

from app.services.dictionary import cache
from app.services.dictionary.schemas import DictionaryResult


class DictionaryApiProvider:
    """Free Dictionary API 提供者"""

    BASE_URL = os.getenv(
        "DICT_PROVIDER_URL",
        "https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
    )

    def fetch(self, word: str) -> dict[str, Any]:
        """
        获取单词释义。
        优先查缓存；缓存未命中则调用第三方 API 并写入缓存。
        返回字典可直接被 DictionaryResult.parse() 消费。
        """
        normalized = word.lower().strip()
        cached = cache.get(normalized)
        if cached is not None:
            result = DictionaryResult.model_validate(cached)
            result.cached = True
            return result.model_dump()

        raw = self._fetch_from_api(normalized)
        # 写入缓存（使用原始 API 响应，不含 cached 字段）
        cache.set(normalized, raw)

        # 再从缓存读取（含 cached=False）
        result = DictionaryResult.model_validate(cache.get(normalized))
        return result.model_dump()

    def _fetch_from_api(self, word: str) -> dict[str, Any]:
        """调用 Free Dictionary API 并解析响应"""
        url = self.BASE_URL.format(word=word)
        with httpx.AsyncClient(timeout=10.0) as client:
            response = client.get(url)
            if response.status_code == 404:
                raise ValueError(f"Word not found: {word}")
            response.raise_for_status()
            raw = cast(list[dict[str, Any]], response.json())

        if not raw:
            raise ValueError(f"Empty response for word: {word}")

        entry = raw[0]
        return self._parse_response(word, entry)

    def _parse_response(self, word: str, entry: dict[str, Any]) -> dict[str, Any]:
        """解析 Free Dictionary API 单条 entry"""
        # 音标
        phonetic = entry.get("phonetic")
        if not phonetic and entry.get("phonetics"):
            for p in entry["phonetics"]:
                if p.get("text"):
                    phonetic = p["text"]
                    break

        # 音频 URL
        audio_url: str | None = None
        for p in entry.get("phonetics", []):
            if p.get("audio"):
                audio_url = p["audio"]
                break

        # 释义
        meanings: list[dict[str, Any]] = []
        for m in entry.get("meanings", []):
            definitions: list[dict[str, Any]] = []
            for d in m.get("definitions", []):
                definitions.append({
                    "meaning": d.get("definition", ""),
                    "example": d.get("example"),
                    "example_translation": None,
                })
            meanings.append({
                "part_of_speech": m.get("partOfSpeech", ""),
                "definitions": definitions,
            })

        return {
            "word": word,
            "phonetic": phonetic,
            "audio_url": audio_url,
            "meanings": meanings,
        }

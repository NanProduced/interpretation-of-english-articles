"""词典服务。"""

from __future__ import annotations

import re
from typing import Any

from app.services.dictionary.providers import Tecd3Provider


class LookupError(Exception):
    """词典查询失败（词不存在）。"""


class DictionaryService:
    _ALIAS_MAP: dict[str, str] = {
        "u.s.": "us",
        "u.k.": "uk",
        "e.g.": "eg",
        "i.e.": "ie",
        "prof.": "prof",
        "dr.": "dr",
        "mr.": "mr",
        "mrs.": "mrs",
        "ms.": "ms",
        "vs.": "vs",
        "etc.": "etc",
    }
    _TRANSLATION_MAP = str.maketrans(
        {
            "’": "'",
            "‘": "'",
            "“": '"',
            "”": '"',
            "⁰": "0",
            "¹": "1",
            "²": "2",
            "³": "3",
            "⁴": "4",
            "⁵": "5",
            "⁶": "6",
            "⁷": "7",
            "⁸": "8",
            "⁹": "9",
        }
    )

    def __init__(self) -> None:
        self._provider = Tecd3Provider()

    async def lookup(self, word: str) -> dict[str, Any]:
        normalized = self._normalize(word)
        try:
            return await self._provider.fetch(normalized)
        except ValueError:
            raise LookupError(f"Word not found: {word}") from None

    async def lookup_entry(self, entry_id: int) -> dict[str, Any]:
        try:
            return await self._provider.fetch_entry(entry_id)
        except ValueError:
            raise LookupError(f"Entry not found: {entry_id}") from None

    def _normalize(self, word: str) -> str:
        normalized = word.strip().translate(self._TRANSLATION_MAP).lower()
        normalized = normalized.replace("·", "").replace("•", "")
        normalized = re.sub(r"(?<=\S)\s+([0-9]+)$", r"\1", normalized)
        normalized = self._ALIAS_MAP.get(normalized, normalized)
        normalized = re.sub(r"^[^\w]+|[^\w]+$", "", normalized)
        normalized = self._ALIAS_MAP.get(normalized, normalized)
        return normalized


_service: DictionaryService | None = None


def get_service() -> DictionaryService:
    global _service
    if _service is None:
        _service = DictionaryService()
    return _service

"""
TECD3 本地词典 Provider。

使用 PostgreSQL 中的 dict_entries / dict_lookup_targets 提供查询能力。

Lookup 优先级：
1. exact headword / lookup target
2. redirect
3. disambiguation
4. .nlp imported lookup targets
5. lemma fallback（LemmInflect 还原词形后再查）
6. 404
"""

from __future__ import annotations

from typing import Any

from app.services.dictionary.cache import get as cache_get
from app.services.dictionary.cache import set as cache_set
from app.services.dictionary.db_pg import CandidateRow, EntryRow, fetch_entry, lookup_candidates
from app.services.dictionary.lemma import get_lemma_candidates
from app.services.dictionary.schemas import (
    DictionaryCandidate,
    DictionaryDisambiguationResult,
    DictionaryEntryPayload,
    DictionaryEntryResult,
    DictionaryExample,
    DictionaryMeaning,
    DictionaryPhrase,
    validate_lookup_result,
)


class Tecd3Provider:
    source = "tecd3"
    cache_version = "v3"

    async def fetch(self, query: str) -> dict[str, Any]:
        cache_key = f"{self.source}:{self.cache_version}:query:{query}"
        cached = cache_get(cache_key)
        if cached is not None:
            result = validate_lookup_result(cached)
            result["cached"] = True
            return result

        candidates = await lookup_candidates(query, source=self.source)
        if not candidates:
            # 只有单词查询（非短语）才尝试 lemma fallback
            if " " not in query:
                candidates = await self._lemma_fallback(query)
            if not candidates:
                raise ValueError(f"Word not found: {query}")

        if len(candidates) == 1:
            entry = await fetch_entry(candidates[0].entry_id, source=self.source)
            if entry is None:
                raise ValueError(f"Word not found: {query}")
            result = self._build_entry_result(query, entry)
        else:
            result = self._build_disambiguation_result(query, candidates)

        cache_set(cache_key, result)
        return result

    async def _lemma_fallback(self, query: str) -> list[CandidateRow]:
        """
        通过 LemmInflect 还原词形，用还原后的 lemma 候选查询词典。

        策略：收集所有 lemma 命中的候选，去重后返回完整列表。
        这样 "axes" / "leaves" 等多歧义词可以触发 disambiguation，
        而单 lemma 命中（如 "humans" → "human"）仍走 entry 分支。
        """
        lemma_candidates = get_lemma_candidates(query)
        all_rows: list[CandidateRow] = []
        seen_entry_ids: set[int] = set()

        for lemma in lemma_candidates:
            rows = await lookup_candidates(lemma, source=self.source)
            for row in rows:
                if row.entry_id not in seen_entry_ids:
                    seen_entry_ids.add(row.entry_id)
                    all_rows.append(row)

        # 按 rank + id 排序，保持与原始 lookup 一致的顺序
        all_rows.sort(key=lambda r: (r.rank, r.entry_id))
        return all_rows


    async def fetch_entry(self, entry_id: int) -> dict[str, Any]:
        cache_key = f"{self.source}:{self.cache_version}:entry:{entry_id}"
        cached = cache_get(cache_key)
        if cached is not None:
            result = validate_lookup_result(cached)
            result["cached"] = True
            return result

        entry = await fetch_entry(entry_id, source=self.source)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")

        result = self._build_entry_result(entry.display_headword, entry)
        cache_set(cache_key, result)
        return result

    def _build_entry_result(self, query: str, entry: EntryRow) -> dict[str, Any]:
        payload = DictionaryEntryPayload(
            id=entry.id,
            word=entry.display_headword,
            base_word=entry.base_headword,
            homograph_no=entry.homograph_no,
            phonetic=entry.phonetic,
            primary_pos=entry.primary_pos,
            meanings=self._parse_meanings(entry),
            examples=self._parse_examples(entry),
            phrases=self._parse_phrases(entry),
            entry_kind=entry.entry_kind,  # type: ignore[arg-type]
        )
        return DictionaryEntryResult(
            query=query,
            provider=self.source,
            cached=False,
            entry=payload,
        ).model_dump()

    def _build_disambiguation_result(self, query: str, candidates: list[CandidateRow]) -> dict[str, Any]:
        payload = [
            DictionaryCandidate(
                entry_id=item.entry_id,
                label=item.target_label,
                part_of_speech=item.target_pos,
                preview=item.preview_text,
                entry_kind=item.entry_kind,  # type: ignore[arg-type]
            )
            for item in candidates
        ]
        return DictionaryDisambiguationResult(
            query=query,
            provider=self.source,
            cached=False,
            candidates=payload,
        ).model_dump()

    def _parse_meanings(self, entry: EntryRow) -> list[DictionaryMeaning]:
        return [
            DictionaryMeaning.model_validate(item)
            for item in entry.meanings_json
            if item
        ]

    def _parse_examples(self, entry: EntryRow) -> list[DictionaryExample]:
        return [
            DictionaryExample.model_validate(item)
            for item in entry.examples_json
            if item
        ]

    def _parse_phrases(self, entry: EntryRow) -> list[DictionaryPhrase]:
        return [
            DictionaryPhrase.model_validate(item)
            for item in entry.phrases_json
            if item
        ]

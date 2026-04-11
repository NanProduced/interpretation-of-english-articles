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
from app.services.dictionary.db_pg import CandidateRow, EntryRow, fetch_entry, lookup_candidates_batch
from app.services.dictionary.lemma import get_lemma_candidates
from app.services.dictionary.schemas import (
    DictionaryCandidate,
    DictionaryDisambiguationResult,
    DictionaryEntryPayload,
    DictionaryEntryResult,
    DictionaryExample,
    DictionaryLookupRequest,
    DictionaryMeaning,
    DictionaryPhrase,
    validate_lookup_result,
)


class Tecd3Provider:
    source = "tecd3"
    cache_version = "v3"

    async def fetch(self, request: DictionaryLookupRequest) -> dict[str, Any]:
        import hashlib
        ctx_hash = hashlib.md5(request.context_sentence.encode()).hexdigest()[:8] if request.context_sentence else "none"
        occ = request.occurrence or 0
        cache_key = f"{self.source}:{self.cache_version}:lookup:q={request.query}:type={request.query_type}:ctx={ctx_hash}:occ={occ}:strategy=v1"
        cached = cache_get(cache_key)
        if cached is not None:
            result = validate_lookup_result(cached)
            result["cached"] = True
            return result

        from app.services.dictionary.phrase_candidates import generate_candidates

        # 1. 直接查询 query
        direct_forms = [request.query]
        
        # 2. 如果有 context_sentence，嗅探短语
        context_forms = []
        if request.context_sentence and request.query_type == "word":
            context_forms = generate_candidates(request.query, request.context_sentence, request.occurrence)

        # 3. 如果 query 本身是 phrase，增加 canonical template
        if request.query_type == "phrase":
            from app.services.dictionary.phrase_templates import canonicalize_dictionary_phrase
            template_form = canonicalize_dictionary_phrase(request.query)
            if template_form and template_form != request.query:
                direct_forms.append(template_form)
            
        all_forms = []
        for f in context_forms + direct_forms:
            if f not in all_forms:
                all_forms.append(f)
                
        candidates = await lookup_candidates_batch(all_forms, source=self.source)
        
        # 4. Lemma fallback
        if not candidates and request.query_type == "word" and " " not in request.query:
            lemma_candidates_forms = get_lemma_candidates(request.query)
            lemma_all_forms = []
            lemma_ctx_forms = []
            
            for lemma in lemma_candidates_forms:
                if request.context_sentence:
                    ctx_f = generate_candidates(lemma, request.context_sentence, request.occurrence)
                    lemma_ctx_forms.extend(ctx_f)
                lemma_all_forms.append(lemma)
                
            unique_lemma_forms = []
            for f in lemma_ctx_forms + lemma_all_forms:
                if f not in unique_lemma_forms:
                    unique_lemma_forms.append(f)
                    
            candidates = await lookup_candidates_batch(unique_lemma_forms, source=self.source)
            
            # Update lists to reflect phase priority 2 and 3
            context_forms = lemma_ctx_forms
            direct_forms = lemma_all_forms

        if not candidates:
            raise ValueError(f"Word not found: {request.query}")
            
        # 5. 重排规则
        def get_sort_key(c: CandidateRow):
            # phase_priority:
            # 0: context phrase exact/template match
            # 1: direct phrase/query exact match
            # 2: lemma context phrase match
            # 3: lemma exact match
            
            phase = 3
            if c.normalized_form in context_forms:
                # 区分是不是通过 lemma 生成的 context_forms (如果走到 fallback 那么 context_forms 会被覆盖为 lemma_ctx_forms)
                phase = 2 if getattr(c, '_is_lemma', False) else 0
            elif c.normalized_form in direct_forms:
                phase = 3 if getattr(c, '_is_lemma', False) else 1
                
            # If we didn't track _is_lemma directly, we just infer from checking the direct_forms lists before fallback
            # Since we overwrite context_forms and direct_forms in fallback, the phase number will naturally be 0 or 1 for lemma fallback as well if we don't adjust.
            # To fix this, let's just use the current forms lists. If it hit fallback, all matches are phase 2 or 3 anyway.
            # Let's simplify: if not hit early, it's lemma fallback
            phase = 0
            if c.normalized_form in context_forms:
                phase = 0
            else:
                phase = 1
                
            query_type_priority = 0 if request.query_type == "phrase" and c.lookup_type == "phrase" else 1
            token_count = len(c.normalized_form.split())
            
            match_kind_priority = 4
            if c.match_kind in ("phrase", "phrase_template"):
                match_kind_priority = 0
            elif c.match_kind == "headword":
                match_kind_priority = 1
            elif c.match_kind == "redirect":
                match_kind_priority = 2
            elif c.match_kind == "nlp":
                match_kind_priority = 3
                
            entry_kind_priority = 0 if c.entry_kind == "entry" else 1
            
            return (
                phase,
                query_type_priority,
                -token_count,
                match_kind_priority,
                entry_kind_priority,
                c.rank,
                c.entry_id
            )
            
        candidates.sort(key=get_sort_key)
        
        unique_candidates = []
        seen = set()
        for c in candidates:
            if c.entry_id not in seen:
                seen.add(c.entry_id)
                unique_candidates.append(c)
                
        candidates = unique_candidates

        if len(candidates) == 1:
            entry = await fetch_entry(candidates[0].entry_id, source=self.source)
            if entry is None:
                raise ValueError(f"Word not found: {request.query}")
            result = self._build_entry_result(request.query, entry)
        else:
            result = self._build_disambiguation_result(request.query, candidates)

        cache_set(cache_key, result)
        return result

    async def _lemma_fallback(self, query: str) -> list[CandidateRow]:
        pass


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
                label=item.lookup_label or item.target_label,
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

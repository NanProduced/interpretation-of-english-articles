"""TECD3 Provider integration tests with lemma fallback."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.dictionary.providers.tecd3 import Tecd3Provider


def _make_candidate(entry_id: int, target_label: str) -> object:
    """Create a mock CandidateRow-like object."""
    return _CandidateMock(entry_id=entry_id, target_label=target_label)


def _make_entry(entry_id: int, word: str) -> object:
    """Create a mock EntryRow-like object."""
    return _EntryMock(
        id=entry_id,
        source="tecd3",
        source_entry_key=word,
        entry_kind="entry",
        display_headword=word,
        base_headword=word,
        homograph_no=None,
        primary_pos="n.",
        phonetic=None,
        meanings_json=[],
        examples_json=[],
        phrases_json=[],
        sections_json=[],
        raw_html=None,
        parse_version="1",
    )


class _CandidateMock:
    """Minimal stand-in for db_pg.CandidateRow."""

    def __init__(self, entry_id: int, target_label: str) -> None:
        self.entry_id = entry_id
        self.target_label = target_label
        self.normalized_form = target_label
        self.lookup_label = target_label
        self.target_pos = "n."
        self.preview_text = f"preview for {target_label}"
        self.rank = 1
        self.match_kind = "exact"
        self.entry_kind = "entry"


class _EntryMock:
    """Minimal stand-in for db_pg.EntryRow."""

    def __init__(
        self,
        id: int,
        source: str,
        source_entry_key: str,
        entry_kind: str,
        display_headword: str,
        base_headword: str | None,
        homograph_no: int | None,
        primary_pos: str | None,
        phonetic: str | None,
        meanings_json: list,
        examples_json: list,
        phrases_json: list,
        sections_json: list,
        raw_html: str | None,
        parse_version: str,
    ) -> None:
        self.id = id
        self.source = source
        self.source_entry_key = source_entry_key
        self.entry_kind = entry_kind
        self.display_headword = display_headword
        self.base_headword = base_headword
        self.homograph_no = homograph_no
        self.primary_pos = primary_pos
        self.phonetic = phonetic
        self.meanings_json = meanings_json
        self.examples_json = examples_json
        self.phrases_json = phrases_json
        self.sections_json = sections_json
        self.raw_html = raw_html
        self.parse_version = parse_version


class TestTecd3ProviderLemmaFallback:
    """Test lemma fallback behavior in Tecd3Provider.fetch()."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear L1 cache before each test to prevent cross-test pollution."""
        from app.services.dictionary import cache as cache_module
        cache_module._L1_CACHE.clear()

    @pytest.fixture
    def provider(self) -> Tecd3Provider:
        return Tecd3Provider()

    @pytest.mark.asyncio
    async def test_exact_match_not_disrupted_by_lemma_fallback(
        self, provider: Tecd3Provider
    ) -> None:
        """Exact match takes priority over lemma fallback."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup, patch(
            "app.services.dictionary.providers.tecd3.fetch_entry",
            new_callable=AsyncMock,
        ) as mock_fetch:
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "human":
                    return [_make_candidate(entry_id=1, target_label="human")]
                return []

            async def fake_fetch(entry_id: int, source: str = "tecd3"):
                return _make_entry(entry_id=entry_id, word="human")

            mock_lookup.side_effect = fake_lookup
            mock_fetch.side_effect = fake_fetch

            result = await provider.fetch("human")
            assert result["result_type"] == "entry"
            assert result["entry"]["word"] == "human"
            assert mock_lookup.call_count == 1

    @pytest.mark.asyncio
    async def test_lemma_fallback_fires_for_unknown_word(
        self, provider: Tecd3Provider
    ) -> None:
        """When exact fails, lemma fallback fires for single words."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup, patch(
            "app.services.dictionary.providers.tecd3.fetch_entry",
            new_callable=AsyncMock,
        ) as mock_fetch:
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "human":
                    return [_make_candidate(entry_id=5, target_label="human")]
                return []

            async def fake_fetch(entry_id: int, source: str = "tecd3"):
                return _make_entry(entry_id=entry_id, word="human")

            mock_lookup.side_effect = fake_lookup
            mock_fetch.side_effect = fake_fetch

            result = await provider.fetch("humans")
            assert result["result_type"] == "entry"
            assert result["entry"]["word"] == "human"
            assert mock_lookup.call_count == 2
            assert mock_lookup.call_args_list[0][0][0] == "humans"
            assert mock_lookup.call_args_list[1][0][0] == "human"

    @pytest.mark.asyncio
    async def test_phrase_raises_not_found(self, provider: Tecd3Provider) -> None:
        """Phrases without results raise ValueError (no lemma fallback)."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup:
            mock_lookup.return_value = []

            with pytest.raises(ValueError, match="Word not found"):
                await provider.fetch("hello world")
            assert mock_lookup.call_count == 1

    @pytest.mark.asyncio
    async def test_hopes_falls_back_to_hope(self, provider: Tecd3Provider) -> None:
        """'hopes' lemma fallback to 'hope'."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup, patch(
            "app.services.dictionary.providers.tecd3.fetch_entry",
            new_callable=AsyncMock,
        ) as mock_fetch:
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "hope":
                    return [_make_candidate(entry_id=7, target_label="hope")]
                return []

            async def fake_fetch(entry_id: int, source: str = "tecd3"):
                return _make_entry(entry_id=entry_id, word="hope")

            mock_lookup.side_effect = fake_lookup
            mock_fetch.side_effect = fake_fetch

            result = await provider.fetch("hopes")
            assert result["result_type"] == "entry"
            assert result["entry"]["word"] == "hope"
            assert mock_lookup.call_count == 2

    @pytest.mark.asyncio
    async def test_landings_falls_back_to_landing(
        self, provider: Tecd3Provider
    ) -> None:
        """'landings' lemma fallback to 'landing'."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup, patch(
            "app.services.dictionary.providers.tecd3.fetch_entry",
            new_callable=AsyncMock,
        ) as mock_fetch:
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "landing":
                    return [_make_candidate(entry_id=9, target_label="landing")]
                return []

            async def fake_fetch(entry_id: int, source: str = "tecd3"):
                return _make_entry(entry_id=entry_id, word="landing")

            mock_lookup.side_effect = fake_lookup
            mock_fetch.side_effect = fake_fetch

            result = await provider.fetch("landings")
            assert result["result_type"] == "entry"
            assert result["entry"]["word"] == "landing"

    @pytest.mark.asyncio
    async def test_crewed_falls_back_to_crew(self, provider: Tecd3Provider) -> None:
        """'crewed' lemma fallback to 'crew'."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup, patch(
            "app.services.dictionary.providers.tecd3.fetch_entry",
            new_callable=AsyncMock,
        ) as mock_fetch:
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "crew":
                    return [_make_candidate(entry_id=3, target_label="crew")]
                return []

            async def fake_fetch(entry_id: int, source: str = "tecd3"):
                return _make_entry(entry_id=entry_id, word="crew")

            mock_lookup.side_effect = fake_lookup
            mock_fetch.side_effect = fake_fetch

            result = await provider.fetch("crewed")
            assert result["result_type"] == "entry"
            assert result["entry"]["word"] == "crew"

    @pytest.mark.asyncio
    async def test_disambiguation_not_disrupted_by_lemma_fallback(
        self, provider: Tecd3Provider
    ) -> None:
        """Exact disambiguation (multiple candidates) still works normally."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup:
            mock_lookup.return_value = [
                _make_candidate(entry_id=10, target_label="anti"),
                _make_candidate(entry_id=11, target_label="anti-"),
            ]
            result = await provider.fetch("anti")
            assert result["result_type"] == "disambiguation"
            assert len(result["candidates"]) == 2
            assert mock_lookup.call_count == 1

    @pytest.mark.asyncio
    async def test_lemma_single_hit_returns_entry(
        self, provider: Tecd3Provider
    ) -> None:
        """Single lemma hit → returns entry result (no disambiguation)."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup, patch(
            "app.services.dictionary.providers.tecd3.fetch_entry",
            new_callable=AsyncMock,
        ) as mock_fetch:
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "crew":
                    return [_make_candidate(entry_id=3, target_label="crew")]
                return []

            async def fake_fetch(entry_id: int, source: str = "tecd3"):
                return _make_entry(entry_id=entry_id, word="crew")

            mock_lookup.side_effect = fake_lookup
            mock_fetch.side_effect = fake_fetch

            result = await provider.fetch("crewed")
            assert result["result_type"] == "entry"
            assert result["entry"]["word"] == "crew"

    @pytest.mark.asyncio
    async def test_lemma_multiple_hits_triggers_disambiguation(
        self, provider: Tecd3Provider
    ) -> None:
        """Multiple lemma hits → triggers disambiguation (e.g. axes → axis + axe)."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup:
            # "axes" → noun lemmas: ["axis", "axe"]; both exist in DB
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "axis":
                    return [
                        _make_candidate(entry_id=1, target_label="axis"),
                    ]
                if form == "axe":
                    return [
                        _make_candidate(entry_id=2, target_label="axe"),
                    ]
                return []

            mock_lookup.side_effect = fake_lookup

            result = await provider.fetch("axes")
            assert result["result_type"] == "disambiguation"
            assert len(result["candidates"]) == 2
            labels = {c["label"] for c in result["candidates"]}
            assert labels == {"axis", "axe"}

    @pytest.mark.asyncio
    async def test_lemma_collects_all_hits_not_first_only(
        self, provider: Tecd3Provider
    ) -> None:
        """All lemma hits are collected and deduplicated before returning."""
        with patch(
            "app.services.dictionary.providers.tecd3.lookup_candidates",
            new_callable=AsyncMock,
        ) as mock_lookup, patch(
            "app.services.dictionary.providers.tecd3.fetch_entry",
            new_callable=AsyncMock,
        ) as mock_fetch:
            # Simulate: "axes" exact fails, lemma "axis" hits (entry_id=1),
            # lemma "axe" also hits (entry_id=2) → disambiguation
            async def fake_lookup(form: str, source: str = "tecd3"):
                if form == "axis":
                    return [_make_candidate(entry_id=1, target_label="axis")]
                if form == "axe":
                    return [_make_candidate(entry_id=2, target_label="axe")]
                return []

            async def fake_fetch(entry_id: int, source: str = "tecd3"):
                word = "axis" if entry_id == 1 else "axe"
                return _make_entry(entry_id=entry_id, word=word)

            mock_lookup.side_effect = fake_lookup
            mock_fetch.side_effect = fake_fetch

            result = await provider.fetch("axes")
            # Both lemmas hit → disambiguation, not entry
            assert result["result_type"] == "disambiguation"
            assert len(result["candidates"]) == 2

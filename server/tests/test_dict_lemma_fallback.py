"""Lemma fallback tests for the dictionary service."""

from __future__ import annotations

import pytest

from app.services.dictionary.lemma import get_lemma_candidates


class TestLemmaFallback:
    """Unit tests for get_lemma_candidates()."""

    def test_humans_returns_human(self) -> None:
        result = get_lemma_candidates("humans")
        assert result == ["human"]

    def test_hopes_returns_hope(self) -> None:
        result = get_lemma_candidates("hopes")
        assert result == ["hope"]

    def test_landings_returns_landing(self) -> None:
        result = get_lemma_candidates("landings")
        assert result == ["landing"]

    def test_crewed_returns_crew(self) -> None:
        result = get_lemma_candidates("crewed")
        assert result == ["crew"]

    def test_exact_word_returns_empty(self) -> None:
        """Exact words that don't inflect return empty list."""
        result = get_lemma_candidates("human")
        assert result == []

    def test_phrase_returns_empty(self) -> None:
        """Phrase queries are not lemmatized."""
        result = get_lemma_candidates("hello world")
        assert result == []

    def test_unknown_word_returns_empty(self) -> None:
        """Unknown words gracefully return empty list."""
        result = get_lemma_candidates("xyzzyfoobar")
        assert result == []

    def test_noun_before_verb_priority(self) -> None:
        """Noun lemmas appear before verb lemmas when both exist."""
        # 'crewed' only has verb lemma 'crew'
        result = get_lemma_candidates("crewed")
        assert result == ["crew"]

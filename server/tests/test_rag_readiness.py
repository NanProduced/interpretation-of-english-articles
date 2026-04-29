"""RAG Readiness Gate tests.

Tests for:
- RAG-02: GRAMMAR_RAG_ENABLED config default
- RAG-03: Only grammar can use RAG; vocabulary/translation always baseline
- RAG-04: grammar_rag_service fallback skeleton
- RAG-08: debug info structure
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from app.schemas.internal.execution_plan import GoalExecutionPlan, GoalPolicy
from app.services.analysis.prompting.example_strategy import (
    get_grammar_example_strategy,
    get_translation_example_strategy,
    get_vocabulary_example_strategy,
)


def _make_plan(few_shot_mode: str = "baseline") -> GoalExecutionPlan:
    """Create a minimal GoalExecutionPlan for testing."""
    return GoalExecutionPlan(
        goal_id="daily_reading",
        variant_id="intermediate_reading",
        topology_mode="learning",
        output_mode="learning_scene",
        prompt_profile="standard",
        few_shot_mode=few_shot_mode,
        policy=GoalPolicy(
            annotation_density=3,
            vocabulary_focus="high_value_only",
            grammar_focus="structural",
            translation_focus="natural",
        ),
    )


# ---------------------------------------------------------------------------
# RAG-02: Config default
# ---------------------------------------------------------------------------

class TestRAGConfig:
    def test_grammar_rag_enabled_defaults_to_false(self):
        """GRAMMAR_RAG_ENABLED should default to False."""
        from app.config.settings import Settings
        s = Settings()
        assert s.grammar_rag_enabled is False


# ---------------------------------------------------------------------------
# RAG-03: Only grammar can use RAG
# ---------------------------------------------------------------------------

class TestRAGRestriction:
    """Verify vocabulary and translation never activate RAG."""

    def test_vocabulary_rag_mode_falls_back_to_baseline(self):
        plan = _make_plan(few_shot_mode="rag")
        strategy = get_vocabulary_example_strategy(plan, sentences=[{"sentence_id": "s1", "text": "Test"}])
        assert strategy.selection_mode == "baseline"

    def test_translation_rag_mode_falls_back_to_baseline(self):
        plan = _make_plan(few_shot_mode="rag")
        strategy = get_translation_example_strategy(plan, sentences=[{"sentence_id": "s1", "text": "Test"}])
        assert strategy.selection_mode == "baseline"

    @patch("app.services.analysis.prompting.example_strategy.get_settings")
    def test_grammar_rag_disabled_falls_back_to_baseline(self, mock_settings):
        """When GRAMMAR_RAG_ENABLED=false, grammar also returns baseline."""
        mock_settings.return_value.grammar_rag_enabled = False
        plan = _make_plan(few_shot_mode="rag")
        strategy = get_grammar_example_strategy(plan, sentences=[{"sentence_id": "s1", "text": "Test"}])
        assert strategy.selection_mode == "baseline"

    @patch("app.services.analysis.prompting.example_strategy.get_settings")
    def test_grammar_rag_enabled_attempts_rag_then_fallback(self, mock_settings):
        """When GRAMMAR_RAG_ENABLED=true but RAG returns empty, falls back to rag_fallback."""
        mock_settings.return_value.grammar_rag_enabled = True
        plan = _make_plan(few_shot_mode="rag")
        strategy = get_grammar_example_strategy(plan, sentences=[{"sentence_id": "s1", "text": "Test"}])
        # Current skeleton returns empty → should fallback
        assert strategy.selection_mode == "rag_fallback"


# ---------------------------------------------------------------------------
# RAG-04: Fallback skeleton
# ---------------------------------------------------------------------------

class TestGrammarRAGFallback:
    @pytest.mark.anyio
    async def test_empty_sentences_returns_fallback(self):
        from app.services.analysis.prompting.rag.grammar_rag_service import query_grammar_rag
        result = await query_grammar_rag("gaokao", [])
        assert result.is_fallback
        assert result.fallback_reason == "no_input_sentences"
        assert result.examples == []

    @pytest.mark.anyio
    async def test_normal_sentences_returns_empty_candidates_fallback(self):
        from app.services.analysis.prompting.rag.grammar_rag_service import query_grammar_rag
        result = await query_grammar_rag(
            "gaokao",
            [{"sentence_id": "s1", "text": "Inspired by the speech, the students decided to start."}],
        )
        assert result.is_fallback
        assert result.fallback_reason == "empty_candidates"
        assert result.examples == []


# ---------------------------------------------------------------------------
# RAG-08: Debug info structure
# ---------------------------------------------------------------------------

class TestRAGDebugInfo:
    @pytest.mark.anyio
    async def test_debug_info_has_required_fields(self):
        from app.services.analysis.prompting.rag.grammar_rag_service import (
            build_rag_debug_info,
            query_grammar_rag,
        )
        result = await query_grammar_rag("gaokao", [{"sentence_id": "s1", "text": "Test sentence."}])
        info = build_rag_debug_info(result)
        assert "selection_mode" in info
        assert "example_count" in info
        assert "fallback_reason" in info
        assert "query_count" in info
        assert "is_fallback" in info

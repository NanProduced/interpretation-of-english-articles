from app.schemas.common import TextSpan
from app.schemas.internal.analysis import SentenceDraft
from app.services.analysis.anchor_resolution import resolve_anchor
from app.services.analysis.input_preparation import prepare_input
from app.services.analysis.user_rules import derive_user_rules


def test_prepare_input_sanitizes_markup_links_and_code() -> None:
    prepared = prepare_input(
        "<div>Hello</div> Visit https://example.com now.\n\n```python\nprint('x')\n```"
    )

    assert prepared.render_text == "Hello\nVisit now."
    assert "remove_url" in prepared.sanitize_report.actions
    assert "remove_code_fence" in prepared.sanitize_report.actions
    assert prepared.sentences[0].text == "Hello\nVisit now."


def test_derive_user_rules_preserves_beginner_goal_but_keeps_advanced_collapsed() -> None:
    rules = derive_user_rules("daily_reading", "beginner_reading")

    assert rules.profile_id == "daily_beginner"
    assert rules.presentation_policy.advanced_default_collapsed is True
    assert rules.annotation_budget.vocabulary_count == 5


def test_resolve_anchor_supports_exact_and_normalized_match() -> None:
    sentence = SentenceDraft(
        sentence_id="s1",
        paragraph_id="p1",
        text='The store said "high-value" products were targeted.',
        sentence_span=TextSpan(start=10, end=59),
    )

    exact = resolve_anchor(sentence, "products")
    normalized = resolve_anchor(sentence, "high value")

    assert exact is not None
    assert exact.start == 38
    assert normalized is not None
    assert normalized.start == 26


def test_resolve_anchor_drops_ambiguous_occurrence_without_index() -> None:
    sentence = SentenceDraft(
        sentence_id="s1",
        paragraph_id="p1",
        text="Chocolate is chocolate for chocolate lovers.",
        sentence_span=TextSpan(start=0, end=42),
    )

    assert resolve_anchor(sentence, "chocolate") is None
    assert resolve_anchor(sentence, "chocolate", anchor_occurrence=2) is not None

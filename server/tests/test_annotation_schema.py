import pytest
from pydantic import ValidationError

from app.schemas.internal.analysis import (
    Chunk,
    ContextGloss,
    GrammarNote,
    PhraseGloss,
    SentenceAnalysis,
    SentenceTranslation,
    SpanRef,
    AnnotationOutput,
    VocabHighlight,
)
from app.services.analysis.validators import (
    validate_context_gloss,
    validate_grammar_note,
    validate_phrase_gloss,
    validate_sentence_analysis,
    validate_annotation_output,
    validate_vocab_highlight,
)


def test_vocab_highlight_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        VocabHighlight(
            sentence_id="s1",
            text="test",
            exam_tags=["cet"],
            definition="bad",
        )


def test_validate_vocab_highlight_anchor_not_substring() -> None:
    result = validate_vocab_highlight(
        VocabHighlight(sentence_id="s1", text="missing", exam_tags=["cet"]),
        {"s1": "This is a test sentence."},
    )
    assert not result.is_valid
    assert any(error["code"] == "anchor_not_substring" for error in result.errors)


def test_validate_phrase_gloss_anchor_not_substring() -> None:
    result = validate_phrase_gloss(
        PhraseGloss(sentence_id="s1", text="missing phrase", phrase_type="collocation", zh="不存在"),
        {"s1": "We need to consider all factors."},
    )
    assert not result.is_valid


def test_validate_context_gloss_anchor_not_substring() -> None:
    result = validate_context_gloss(
        ContextGloss(sentence_id="s1", text="missing", gloss="中文", reason="原因"),
        {"s1": "The word is used here."},
    )
    assert not result.is_valid


def test_validate_grammar_note_spans_not_substring() -> None:
    result = validate_grammar_note(
        GrammarNote(
            sentence_id="s1",
            spans=[SpanRef(text="not_found", role="trigger")],
            label="测试",
            note_zh="测试",
        ),
        {"s1": "So fundamental are these challenges."},
    )
    assert not result.is_valid


def test_validate_sentence_analysis_chunk_not_substring() -> None:
    result = validate_sentence_analysis(
        SentenceAnalysis(
            sentence_id="s1",
            label="测试",
            analysis_zh="测试",
            chunks=[
                Chunk(order=1, label="A", text="This"),
                Chunk(order=2, label="B", text="not_in_sentence"),
            ],
        ),
        {"s1": "This is a test."},
    )
    assert not result.is_valid


def test_validate_annotation_output_requires_full_translations() -> None:
    from app.services.analysis.input_preparation import prepare_input

    prepared = prepare_input("First sentence. Second sentence.")
    output = AnnotationOutput(
        annotations=[
            VocabHighlight(sentence_id="s1", text="First", exam_tags=["cet"]),
        ],
        sentence_translations=[
            SentenceTranslation(sentence_id="s1", translation_zh="第一句。"),
        ],
    )
    result = validate_annotation_output(output, prepared)
    assert not result.is_valid
    assert any(error["code"] == "translation_missing" for error in result.errors)


def test_annotation_output_accepts_mixed_annotations() -> None:
    output = AnnotationOutput(
        annotations=[
            VocabHighlight(sentence_id="s1", text="word", exam_tags=["cet"]),
            PhraseGloss(sentence_id="s1", text="phrase", phrase_type="collocation", zh="短语"),
            ContextGloss(sentence_id="s1", text="context", gloss="语境", reason="原因"),
            GrammarNote(sentence_id="s1", spans=[SpanRef(text="so", role="x")], label="语法", note_zh="注释"),
            SentenceAnalysis(
                sentence_id="s1",
                label="句型",
                analysis_zh="讲解",
                chunks=[Chunk(order=1, label="主", text="Main"), Chunk(order=2, label="谓", text="is")],
            ),
        ],
        sentence_translations=[SentenceTranslation(sentence_id="s1", translation_zh="翻译")],
    )
    assert len(output.annotations) == 5

from app.schemas.analysis import AnalysisResult, AnalyzeRequest


def test_analyze_request_rejects_goal_variant_mismatch() -> None:
    try:
        AnalyzeRequest.model_validate(
            {
                "text": "This is a test article.",
                "reading_goal": "academic",
                "reading_variant": "cet4",
            }
        )
    except Exception as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("expected goal/variant validation error")


def test_analysis_result_schema_accepts_minimal_valid_payload() -> None:
    payload = {
        "schema_version": "1.0.0",
        "request": {
            "request_id": "req-001",
            "source_type": "user_input",
            "reading_goal": "daily_reading",
            "reading_variant": "intermediate_reading",
            "profile_id": "daily_intermediate",
        },
        "status": {
            "state": "success",
            "is_degraded": False,
            "error_code": None,
            "user_message": None,
        },
        "article": {
            "source_type": "user_input",
            "source_text": "This is a test article.",
            "render_text": "This is a test article.",
            "paragraphs": [
                {
                    "paragraph_id": "p1",
                    "text": "This is a test article.",
                    "render_span": {"start": 0, "end": 23},
                    "sentence_ids": ["s1"],
                }
            ],
            "sentences": [
                {
                    "sentence_id": "s1",
                    "paragraph_id": "p1",
                    "text": "This is a test article.",
                    "sentence_span": {"start": 0, "end": 23},
                }
            ],
        },
        "sanitize_report": {
            "actions": ["collapse_spaces"],
            "removed_segment_count": 0,
        },
        "vocabulary_annotations": [],
        "grammar_annotations": [],
        "sentence_annotations": [],
        "render_marks": [],
        "translations": {
            "sentence_translations": [
                {"sentence_id": "s1", "translation_zh": "这是一篇测试文章。"}
            ],
            "full_translation_zh": "这是一篇测试文章。",
        },
        "warnings": [],
        "metrics": {
            "vocabulary_count": 0,
            "grammar_count": 0,
            "sentence_note_count": 0,
            "render_mark_count": 0,
            "sentence_count": 1,
            "paragraph_count": 1,
        },
    }

    result = AnalysisResult.model_validate(payload)

    assert result.schema_version == "1.0.0"
    assert result.request.profile_id == "daily_intermediate"
    assert result.article.sentences[0].sentence_span.start == 0

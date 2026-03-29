from app.schemas.preprocess import PreprocessResult


def test_preprocess_result_schema_accepts_minimal_valid_payload() -> None:
    payload = {
        "schema_version": "0.1.0",
        "request": {
            "request_id": "req-001",
            "profile_key": "exam_cet4",
            "source_type": "user_input",
        },
        "normalized": {
            "source_text": "This is a test.",
            "clean_text": "This is a test.",
            "text_changed": False,
            "normalization_actions": [],
        },
        "segmentation": {
            "paragraph_count": 1,
            "sentence_count": 1,
            "paragraphs": [
                {
                    "paragraph_id": "p1",
                    "text": "This is a test.",
                    "start": 0,
                    "end": 15,
                }
            ],
            "sentences": [
                {
                    "sentence_id": "s1",
                    "paragraph_id": "p1",
                    "text": "This is a test.",
                    "start": 0,
                    "end": 15,
                }
            ],
        },
        "detection": {
            "language": {
                "primary_language": "en",
                "english_ratio": 1.0,
                "non_english_ratio": 0.0,
            },
            "text_type": {
                "predicted_type": "article",
                "confidence": 0.95,
            },
            "noise": {
                "noise_ratio": 0.0,
                "has_html": False,
                "has_code_like_content": False,
                "appears_truncated": False,
            },
        },
        "issues": [],
        "quality": {
            "score": 0.92,
            "grade": "good",
            "suitable_for_full_annotation": True,
            "summary_zh": "文本质量良好，可进入完整解读。",
        },
        "routing": {
            "decision": "full",
            "should_continue": True,
            "degrade_reason": None,
            "reject_reason": None,
        },
        "warnings": [],
    }

    result = PreprocessResult.model_validate(payload)

    assert result.schema_version == "0.1.0"
    assert result.routing.decision.value == "full"
    assert result.quality.grade.value == "good"


import asyncio

from app.workflow import preprocess_nodes as preprocess_nodes
from app.workflow import preprocess as preprocess_workflow
from app.workflow.preprocess import (
    PreprocessState,
    _build_guardrails_trace_metadata,
    detect_language,
    detect_noise,
    detect_text_type,
    normalize_text,
    segment_text,
)
from app.schemas.preprocess import DetectionResult, LanguageDetection, NoiseDetection, PreprocessAnalyzeRequest, TextTypeDetection


def test_normalize_text_collapses_spaces_and_line_breaks() -> None:
    normalized = normalize_text("Hello,\r\n\r\nThis   is   a test.  ")

    assert normalized.clean_text == "Hello,\n\nThis is a test."
    assert normalized.text_changed is True
    assert "normalize_line_breaks" in normalized.normalization_actions


def test_segment_text_returns_paragraphs_and_sentences() -> None:
    segmented = segment_text("First sentence. Second sentence.\n\nThird sentence.")

    assert segmented.paragraph_count == 2
    assert segmented.sentence_count == 3
    assert segmented.paragraphs[0].paragraph_id == "p1"
    assert segmented.sentences[1].sentence_id == "s2"


def test_detect_helpers_flag_noise_and_language() -> None:
    language = detect_language("This is English. 这是中文。")
    noise = detect_noise("<div>Hello</div> ```python")
    text_type = detect_text_type("Short text. Two sentences.", noise=detect_noise("Short text. Two sentences."), sentence_count=2)

    assert language.primary_language in {"en", "mixed"}
    assert 0 < language.english_ratio < 1
    assert noise.has_html is True
    assert noise.has_code_like_content is True
    assert text_type.predicted_type == "article"


def test_run_preprocess_v0_returns_fallback_output(monkeypatch) -> None:
    monkeypatch.setattr(preprocess_nodes, "resolve_model_config", lambda *args, **kwargs: None)
    payload = PreprocessAnalyzeRequest(
        text="<div>This is a test article. It has HTML noise.</div>",
        profile_key="exam_cet4",
        source_type="user_input",
    )
    result = asyncio.run(preprocess_workflow.run_preprocess_v0(payload))
    body = result.model_dump(mode="json")
    assert body["schema_version"] == "0.1.0"
    assert body["request"]["profile_key"] == "exam_cet4"
    assert body["detection"]["noise"]["has_html"] is True
    assert any(item["code"] == "GUARDRAILS_FALLBACK" for item in body["warnings"])


def test_build_guardrails_trace_metadata_contains_preprocess_debug_markers() -> None:
    state: PreprocessState = {
        "payload": PreprocessAnalyzeRequest(
            text="This is a test article.",
            profile_key="exam_cet4",
            source_type="user_input",
            request_id="req-test-1",
        ),
        "request_id": "req-test-1",
    }
    detection = DetectionResult(
        language=LanguageDetection(primary_language="en", english_ratio=1.0, non_english_ratio=0.0),
        text_type=TextTypeDetection(predicted_type="article", confidence=0.8),
        noise=NoiseDetection(
            noise_ratio=0.0,
            has_html=False,
            has_code_like_content=False,
            appears_truncated=False,
        ),
    )

    metadata = _build_guardrails_trace_metadata(state, detection)

    assert metadata["workflow_version"] == "preprocess_v0"
    assert metadata["trace_scope"] == "preprocess_local_debug"
    assert metadata["request_id"] == "req-test-1"
    assert metadata["node"] == "preprocess_guardrails"
    assert metadata["ls_model_name"] is not None

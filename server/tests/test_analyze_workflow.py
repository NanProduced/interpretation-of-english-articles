from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalysisResult
from app.workflow import analyze_nodes as analyze_nodes
from app.schemas.preprocess import (
    DetectionResult,
    LanguageDetection,
    NoiseDetection,
    NormalizedText,
    PreprocessRequestMeta,
    PreprocessResult,
    QualityAssessment,
    QualityGrade,
    RoutingDecision,
    RoutingDecisionType,
    SegmentedParagraph,
    SegmentedSentence,
    SegmentationResult,
    TextTypeDetection,
)
async def _fake_preprocess(*args, **kwargs) -> PreprocessResult:
    return PreprocessResult(
        request=PreprocessRequestMeta(
            request_id="req-test-1",
            profile_key="exam_cet4",
            source_type="user_input",
        ),
        normalized=NormalizedText(
            source_text="This is a test article. It has a second sentence.",
            clean_text="This is a test article. It has a second sentence.",
            text_changed=False,
            normalization_actions=[],
        ),
        segmentation=SegmentationResult(
            paragraph_count=1,
            sentence_count=2,
            paragraphs=[
                SegmentedParagraph(
                    paragraph_id="p1",
                    text="This is a test article. It has a second sentence.",
                    start=0,
                    end=49,
                )
            ],
            sentences=[
                SegmentedSentence(
                    sentence_id="s1",
                    paragraph_id="p1",
                    text="This is a test article.",
                    start=0,
                    end=23,
                ),
                SegmentedSentence(
                    sentence_id="s2",
                    paragraph_id="p1",
                    text="It has a second sentence.",
                    start=24,
                    end=49,
                ),
            ],
        ),
        detection=DetectionResult(
            language=LanguageDetection(primary_language="en", english_ratio=1.0, non_english_ratio=0.0),
            text_type=TextTypeDetection(predicted_type="article", confidence=0.8),
            noise=NoiseDetection(
                noise_ratio=0.0,
                has_html=False,
                has_code_like_content=False,
                appears_truncated=False,
            ),
        ),
        quality=QualityAssessment(
            score=0.9,
            grade=QualityGrade.GOOD,
            suitable_for_full_annotation=True,
            summary_zh="文本质量良好。",
        ),
        routing=RoutingDecision(
            decision=RoutingDecisionType.FULL,
            should_continue=True,
        ),
        warnings=[],
    )


async def _raise_core(*args, **kwargs):
    raise RuntimeError("core failed")


async def _raise_translation(*args, **kwargs):
    raise RuntimeError("translation failed")


def test_analyze_route_returns_complete_payload_with_fallback(monkeypatch) -> None:
    monkeypatch.setattr(analyze_nodes, "run_preprocess_v0", _fake_preprocess)
    monkeypatch.setattr(analyze_nodes, "run_core_llm", _raise_core)
    monkeypatch.setattr(analyze_nodes, "run_translation_llm", _raise_translation)
    client = TestClient(app)

    response = client.post(
        "/analyze",
        json={
            "text": "This is a test article. It has a second sentence.",
            "profile_key": "exam_cet4",
            "source_type": "user_input",
        },
    )

    assert response.status_code == 200
    body = response.json()
    AnalysisResult.model_validate(body)
    assert body["status"]["state"] == "partial_success"
    assert body["article"]["sentences"][0]["sentence_id"] == "s1"
    assert len(body["annotations"]["grammar"]) >= 1
    assert len(body["translations"]["sentence_translations"]) == 2
    assert any(item["code"] == "CORE_AGENT_FALLBACK" for item in body["warnings"])
    assert any(item["code"] == "TRANSLATION_AGENT_FALLBACK" for item in body["warnings"])
    assert body["annotations"]["grammar"][0]["priority"] in {"core", "expand", "reference"}
    assert isinstance(body["annotations"]["grammar"][0]["default_visible"], bool)


def test_analyze_route_rejects_unknown_model_preset() -> None:
    client = TestClient(app)

    response = client.post(
        "/analyze",
        json={
            "text": "This is a test article.",
            "profile_key": "exam_cet4",
            "source_type": "user_input",
            "model_selection": {"preset": "missing_preset"},
        },
    )

    assert response.status_code == 422
    assert "Unknown model preset" in response.json()["detail"]

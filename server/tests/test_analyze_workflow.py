from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import RenderSceneModel
from app.schemas.internal.analysis import (
    SentenceTranslation,
    AnnotationOutput,
    VocabHighlight,
)
from app.services.analysis.input_preparation import prepare_input
from app.services.analysis.projection import project_to_render_scene
from app.services.analysis.user_rules import derive_user_rules
from app.workflow import analyze_nodes


async def _fake_run_annotation_span(*args, **kwargs) -> AnnotationOutput:
    return AnnotationOutput(
        annotations=[VocabHighlight(sentence_id="s1", text="extreme lengths", exam_tags=["cet"])],
        sentence_translations=[
            SentenceTranslation(sentence_id="s1", translation_zh="店主不得不采取极端措施阻止商店扒手。"),
            SentenceTranslation(sentence_id="s2", translation_zh="令人不安的是，每天都有针对店员的暴力事件。"),
        ],
    )


async def _raise_annotation_span(*args, **kwargs):
    raise RuntimeError("annotation failed")

async def _invalid_annotation_span(*args, **kwargs) -> AnnotationOutput:
    return AnnotationOutput(
        annotations=[VocabHighlight(sentence_id="s1", text="missing_anchor", exam_tags=["cet"])],
        sentence_translations=[
            SentenceTranslation(sentence_id="s1", translation_zh="店主不得不采取极端措施阻止商店扒手。"),
        ],
    )


def test_analyze_route_returns_v21_payload(monkeypatch) -> None:
    monkeypatch.setattr(analyze_nodes, "_run_annotation_llm_span", _fake_run_annotation_span)
    client = TestClient(app)
    response = client.post(
        "/analyze",
        json={
            "text": (
                "Shopkeepers are having to go to extreme lengths to stop shoplifters. "
                "Disturbingly, there are daily incidents of violence against workers."
            ),
            "reading_goal": "daily_reading",
            "reading_variant": "beginner_reading",
            "source_type": "user_input",
        },
    )
    assert response.status_code == 200
    body = response.json()
    RenderSceneModel.model_validate(body)
    assert body["schema_version"] == "2.1.0"
    assert body["request"]["profile_id"] == "daily_beginner"
    assert len(body["inline_marks"]) == 1
    assert len(body["sentence_entries"]) == 0
    assert len(body["translations"]) == 2


def test_analyze_route_rejects_unknown_model_preset() -> None:
    client = TestClient(app)
    response = client.post(
        "/analyze",
        json={
            "text": "This is a test article.",
            "reading_goal": "daily_reading",
            "reading_variant": "intermediate_reading",
            "source_type": "user_input",
            "model_selection": {"preset": "missing_preset"},
        },
    )
    assert response.status_code == 422
    assert "Unknown model preset" in response.json()["detail"]


def test_analyze_route_returns_empty_result_when_teacher_fails(monkeypatch) -> None:
    monkeypatch.setattr(analyze_nodes, "_run_annotation_llm_span", _raise_annotation_span)
    client = TestClient(app)
    response = client.post(
        "/analyze",
        json={
            "text": "This is a valid article. It has two sentences.",
            "reading_goal": "exam",
            "reading_variant": "cet",
            "source_type": "user_input",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert any(warning.get("code") == "ANNOTATION_GENERATION_FAILED" for warning in body.get("warnings", []))
    assert body["inline_marks"] == []
    assert body["sentence_entries"] == []

def test_analyze_route_surfaces_runtime_validation_warnings(monkeypatch) -> None:
    monkeypatch.setattr(analyze_nodes, "_run_annotation_llm_span", _invalid_annotation_span)
    client = TestClient(app)
    response = client.post(
        "/analyze",
        json={
            "text": (
                "Shopkeepers are having to go to extreme lengths to stop shoplifters. "
                "Disturbingly, there are daily incidents of violence against workers."
            ),
            "reading_goal": "daily_reading",
            "reading_variant": "beginner_reading",
            "source_type": "user_input",
        },
    )
    assert response.status_code == 200
    body = response.json()
    warning_codes = {warning["code"] for warning in body["warnings"]}
    assert "VALIDATION_ANCHOR_NOT_SUBSTRING" in warning_codes
    assert "VALIDATION_TRANSLATION_MISSING" in warning_codes


def test_projection_keeps_stable_ids_when_prior_mark_is_dropped() -> None:
    prepared_input = prepare_input("This sentence mentions this first. Another sentence mentions leverage clearly.")
    user_rules = derive_user_rules("daily_reading", "intermediate_reading")

    baseline = project_to_render_scene(
        annotation_output=AnnotationOutput(
        annotations=[VocabHighlight(sentence_id="s2", text="leverage", exam_tags=["cet"])],
            sentence_translations=[
                SentenceTranslation(sentence_id="s1", translation_zh="第一句先提到了 this。"),
                SentenceTranslation(sentence_id="s2", translation_zh="第二句清楚地提到了 leverage。"),
            ],
        ),
        prepared_input=prepared_input,
        source_type="user_input",
        reading_goal="daily_reading",
        reading_variant="intermediate_reading",
        profile_id=user_rules.profile_id,
        request_id="req-1",
    )

    with_dropped_prefix = project_to_render_scene(
        annotation_output=AnnotationOutput(
            annotations=[
                VocabHighlight(sentence_id="s1", text="missing_anchor", exam_tags=["cet"]),
                VocabHighlight(sentence_id="s2", text="leverage", exam_tags=["cet"]),
            ],
            sentence_translations=[
                SentenceTranslation(sentence_id="s1", translation_zh="第一句先提到了 this。"),
                SentenceTranslation(sentence_id="s2", translation_zh="第二句清楚地提到了 leverage。"),
            ],
        ),
        prepared_input=prepared_input,
        source_type="user_input",
        reading_goal="daily_reading",
        reading_variant="intermediate_reading",
        profile_id=user_rules.profile_id,
        request_id="req-2",
    )

    assert baseline.result.inline_marks[0].id == with_dropped_prefix.result.inline_marks[0].id
    assert with_dropped_prefix.dropped_count == 1

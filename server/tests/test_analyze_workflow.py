from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import AnalysisResult
from app.schemas.internal.analysis import (
    AnnotationDraft,
    SentenceTranslationDraft,
    TeachingOutput,
)
from app.workflow import analyze_nodes


async def _fake_run_annotation_llm(*args, **kwargs) -> TeachingOutput:
    return TeachingOutput(
        vocabulary_annotations=[
            AnnotationDraft(
                sentence_id="s1",
                anchor_text="extreme lengths",
                title="固定搭配",
                content="这里表示采取极端措施。",
                pedagogy_level="core",
            )
        ],
        grammar_annotations=[
            AnnotationDraft(
                sentence_id="s1",
                anchor_text="are having to",
                title="have to 结构",
                content="这里表示不得不做某事。",
                pedagogy_level="support",
            )
        ],
        sentence_annotations=[
            AnnotationDraft(
                sentence_id="s2",
                anchor_text="Disturbingly",
                title="句首态度副词",
                content="这里先用副词提示说话人的态度。",
                pedagogy_level="advanced",
            )
        ],
        sentence_translations=[
            SentenceTranslationDraft(
                sentence_id="s1",
                translation_zh="店主不得不采取极端措施阻止巧克力被偷。",
            ),
            SentenceTranslationDraft(
                sentence_id="s2",
                translation_zh="令人不安的是，每天都有针对店员的暴力事件。",
            ),
        ],
    )


async def _raise_annotation_llm(*args, **kwargs):
    raise RuntimeError("annotation failed")


def test_analyze_route_returns_v1_payload(monkeypatch) -> None:
    monkeypatch.setattr(analyze_nodes, "run_annotation_llm", _fake_run_annotation_llm)
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
    AnalysisResult.model_validate(body)
    assert body["schema_version"] == "1.0.0"
    assert body["status"]["state"] == "success"
    assert body["request"]["reading_goal"] == "daily_reading"
    assert body["request"]["reading_variant"] == "beginner_reading"
    assert body["request"]["profile_id"] == "daily_beginner"
    assert len(body["vocabulary_annotations"]) == 1
    assert len(body["grammar_annotations"]) == 1
    assert len(body["sentence_annotations"]) == 1
    assert len(body["render_marks"]) == 3
    assert len(body["translations"]["sentence_translations"]) == 2
    assert body["translations"]["full_translation_zh"]


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


def test_analyze_route_returns_failed_status_when_teacher_fails(monkeypatch) -> None:
    monkeypatch.setattr(analyze_nodes, "run_annotation_llm", _raise_annotation_llm)
    client = TestClient(app)

    response = client.post(
        "/analyze",
        json={
            "text": "This is a valid article. It has two sentences.",
            "reading_goal": "exam",
            "reading_variant": "cet4",
            "source_type": "user_input",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"]["state"] == "failed"
    assert body["status"]["error_code"] == "ANNOTATION_GENERATION_FAILED"
    assert body["vocabulary_annotations"] == []
    assert body["render_marks"] == []

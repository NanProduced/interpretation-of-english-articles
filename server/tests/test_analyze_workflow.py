from fastapi.testclient import TestClient

from app.main import app
from app.schemas.analysis import RenderSceneModel
from app.schemas.internal.analysis import (
    InlineMarkDraft,
    SentenceEntryDraft,
    SentenceTranslationDraft,
    TeachingOutput,
    TextAnchor,
)
from app.services.analysis.input_preparation import prepare_input
from app.services.analysis.result_assembly import assemble_result
from app.services.analysis.user_rules import derive_user_rules
from app.workflow import analyze_nodes


async def _fake_run_annotation_llm(*args, **kwargs) -> TeachingOutput:
    return TeachingOutput(
        inline_marks=[
            InlineMarkDraft(
                anchor=TextAnchor(
                    kind="text",
                    sentence_id="s1",
                    anchor_text="extreme lengths",
                ),
                tone="phrase",
                render_type="background",
                clickable=True,
            )
        ],
        sentence_entries=[
            SentenceEntryDraft(
                sentence_id="s1",
                label="语法",
                entry_type="grammar",
                title="have to 结构",
                content="这里表示不得不做某事。",
            )
        ],
        cards=[],
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


def test_analyze_route_returns_v2_payload(monkeypatch) -> None:
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
    RenderSceneModel.model_validate(body)
    assert body["schema_version"] == "2.0.0"
    assert body["request"]["reading_goal"] == "daily_reading"
    assert body["request"]["reading_variant"] == "beginner_reading"
    assert body["request"]["profile_id"] == "daily_beginner"
    assert len(body["inline_marks"]) == 1
    assert len(body["sentence_entries"]) == 1
    assert len(body["translations"]) == 2
    assert body["cards"] == []


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
    # V2: error is reflected in warnings
    assert any(w.get("code") == "ANNOTATION_GENERATION_FAILED" for w in body.get("warnings", []))
    assert body["inline_marks"] == []
    assert body["cards"] == []


def test_assemble_result_keeps_stable_ids_when_prior_mark_is_dropped() -> None:
    prepared_input = prepare_input(
        "This sentence mentions this first. Another sentence mentions leverage clearly."
    )
    user_rules = derive_user_rules("daily_reading", "intermediate_reading")

    baseline = assemble_result(
        request_id="req-1",
        source_type="user_input",
        reading_goal="daily_reading",
        reading_variant="intermediate_reading",
        prepared_input=prepared_input,
        user_rules=user_rules,
        teaching_output=TeachingOutput(
            inline_marks=[
                InlineMarkDraft(
                    anchor=TextAnchor(
                        kind="text",
                        sentence_id="s2",
                        anchor_text="leverage",
                    ),
                    tone="focus",
                    render_type="background",
                    clickable=True,
                )
            ],
            sentence_entries=[],
            cards=[],
            sentence_translations=[
                SentenceTranslationDraft(
                    sentence_id="s1",
                    translation_zh="第一句先提到了 this。",
                ),
                SentenceTranslationDraft(
                    sentence_id="s2",
                    translation_zh="第二句清楚地提到了 leverage。",
                ),
            ],
        ),
    )

    with_dropped_prefix = assemble_result(
        request_id="req-2",
        source_type="user_input",
        reading_goal="daily_reading",
        reading_variant="intermediate_reading",
        prepared_input=prepared_input,
        user_rules=user_rules,
        teaching_output=TeachingOutput(
            inline_marks=[
                InlineMarkDraft(
                    anchor=TextAnchor(
                        kind="text",
                        sentence_id="s1",
                        anchor_text="this",
                    ),
                    tone="focus",
                    render_type="background",
                    clickable=True,
                ),
                InlineMarkDraft(
                    anchor=TextAnchor(
                        kind="text",
                        sentence_id="s2",
                        anchor_text="leverage",
                    ),
                    tone="focus",
                    render_type="background",
                    clickable=True,
                ),
            ],
            sentence_entries=[],
            cards=[],
            sentence_translations=[
                SentenceTranslationDraft(
                    sentence_id="s1",
                    translation_zh="第一句先提到了 this。",
                ),
                SentenceTranslationDraft(
                    sentence_id="s2",
                    translation_zh="第二句清楚地提到了 leverage。",
                ),
            ],
        ),
    )

    assert baseline.result.inline_marks[0].id == with_dropped_prefix.result.inline_marks[0].id
    assert with_dropped_prefix.dropped_count == 1

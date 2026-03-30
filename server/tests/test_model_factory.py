import json

from app.agents.model_factory import (
    MODEL_ROUTE_ANALYSIS_CORE,
    MODEL_ROUTE_ANALYSIS_TRANSLATION,
    MODEL_ROUTE_PREPROCESS_GUARDRAILS,
    ModelSelectionError,
    resolve_model_config,
)
from app.config.settings import Settings
from app.llm.model_selection import ModelSelection, RouteModelSelection
from app.workflow.tracing import infer_model_provider


def test_resolve_model_config_keeps_legacy_behavior() -> None:
    settings = Settings(
        analysis_model_name="Qwen/Qwen3-8B",
        analysis_base_url="http://127.0.0.1:8000/v1",
        analysis_api_key="",
        guardrails_model_name="Qwen/Qwen3-8B",
        guardrails_base_url="http://127.0.0.1:8000/v1",
        guardrails_api_key="",
    )

    core_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_CORE)
    translation_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_TRANSLATION)
    preprocess_model = resolve_model_config(settings, MODEL_ROUTE_PREPROCESS_GUARDRAILS)

    assert core_model is not None
    assert core_model.profile_name == "legacy_analysis"
    assert core_model.model_name == "Qwen/Qwen3-8B"

    assert translation_model is not None
    assert translation_model.profile_name == "legacy_analysis"

    assert preprocess_model is not None
    assert preprocess_model.profile_name == "legacy_guardrails"


def test_resolve_model_config_supports_per_node_profiles() -> None:
    settings = Settings(
        default_model_profile="local_qwen",
        translation_model_profile="minimax_m27",
        model_profiles_json=json.dumps(
            {
                "local_qwen": {
                    "model_name": "Qwen/Qwen3-8B",
                    "base_url": "http://127.0.0.1:8000/v1",
                    "api_key": "",
                }
            }
        ),
        minimax_m27_base_url="https://api.minimax.io/v1",
        minimax_m27_api_key="test-minimax-key",
    )

    core_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_CORE)
    translation_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_TRANSLATION)

    assert core_model is not None
    assert core_model.profile_name == "local_qwen"
    assert core_model.model_name == "Qwen/Qwen3-8B"

    assert translation_model is not None
    assert translation_model.profile_name == "minimax_m27"
    assert translation_model.model_name == "MiniMax-M2.7"
    assert translation_model.base_url == "https://api.minimax.io/v1"
    assert infer_model_provider(translation_model.base_url) == "minimax"


def test_resolve_model_config_supports_runtime_overrides_and_presets() -> None:
    settings = Settings(
        core_model_profile="local_qwen",
        model_profiles_json=json.dumps(
            {
                "local_qwen": {
                    "model_name": "Qwen/Qwen3-8B",
                    "base_url": "http://127.0.0.1:8000/v1",
                    "api_key": "",
                },
                "gpt4o_like": {
                    "model_name": "gpt-4o-mini",
                    "base_url": "https://api.example.com/v1",
                    "api_key": "key",
                },
            }
        ),
        model_presets_json=json.dumps(
            {
                "quality_eval": {
                    "routes": {
                        "analysis_core": {"profile": "gpt4o_like"},
                        "analysis_translation": {"profile": "gpt4o_like"},
                    }
                }
            }
        ),
        minimax_m27_base_url="https://api.minimax.io/v1",
    )
    selection = ModelSelection(
        preset="quality_eval",
        routes={
            MODEL_ROUTE_ANALYSIS_TRANSLATION: RouteModelSelection(profile="minimax_m27"),
        },
    )

    core_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_CORE, selection)
    translation_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_TRANSLATION, selection)

    assert core_model is not None
    assert core_model.profile_name == "gpt4o_like"

    assert translation_model is not None
    assert translation_model.profile_name == "minimax_m27"


def test_resolve_model_config_rejects_unknown_preset() -> None:
    settings = Settings()

    try:
        resolve_model_config(
            settings,
            MODEL_ROUTE_ANALYSIS_CORE,
            ModelSelection(preset="missing_preset"),
        )
    except ModelSelectionError as exc:
        assert "Unknown model preset" in str(exc)
    else:
        raise AssertionError("expected ModelSelectionError for unknown preset")

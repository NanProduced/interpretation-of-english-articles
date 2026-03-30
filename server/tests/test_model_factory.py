import json

from app.config.settings import Settings
from app.llm.router import ModelSelectionError, resolve_model_config
from app.llm.routes import (
    MODEL_ROUTE_ANALYSIS_CORE,
    MODEL_ROUTE_ANALYSIS_TRANSLATION,
    MODEL_ROUTE_PREPROCESS_GUARDRAILS,
)
from app.llm.types import ModelSelection, RouteModelSelection


def test_resolve_model_config_uses_route_defaults_and_profiles() -> None:
    settings = Settings(
        default_model_profile="local_qwen",
        translation_model_profile="minimax_m27",
        model_profiles_json=json.dumps(
            {
                "local_qwen": {
                    "provider": "openai_compatible",
                    "model_name": "Qwen/Qwen3-8B",
                    "base_url": "http://127.0.0.1:8000/v1",
                    "api_key": "",
                },
                "minimax_m27": {
                    "provider": "openai_compatible",
                    "model_name": "MiniMax-M2.7",
                    "base_url": "https://api.minimax.io/v1",
                    "api_key": "test-minimax-key",
                },
            }
        ),
    )

    core_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_CORE)
    translation_model = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_TRANSLATION)

    assert core_model is not None
    assert core_model.profile_name == "local_qwen"
    assert core_model.model_name == "Qwen/Qwen3-8B"
    assert core_model.provider == "openai_compatible"

    assert translation_model is not None
    assert translation_model.profile_name == "minimax_m27"
    assert translation_model.model_name == "MiniMax-M2.7"
    assert translation_model.base_url == "https://api.minimax.io/v1"


def test_resolve_model_config_supports_runtime_overrides_and_presets() -> None:
    settings = Settings(
        core_model_profile="local_qwen",
        model_profiles_json=json.dumps(
            {
                "local_qwen": {
                    "provider": "openai_compatible",
                    "model_name": "Qwen/Qwen3-8B",
                    "base_url": "http://127.0.0.1:8000/v1",
                    "api_key": "",
                },
                "gpt4o_like": {
                    "provider": "openai_compatible",
                    "model_name": "gpt-4o-mini",
                    "base_url": "https://api.example.com/v1",
                    "api_key": "key",
                },
                "minimax_m27": {
                    "provider": "openai_compatible",
                    "model_name": "MiniMax-M2.7",
                    "base_url": "https://api.minimax.io/v1",
                    "api_key": "test-minimax-key",
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


def test_resolve_model_config_supports_preprocess_route() -> None:
    settings = Settings(
        preprocess_model_profile="guardrails_local",
        model_profiles_json=json.dumps(
            {
                "guardrails_local": {
                    "provider": "openai_compatible",
                    "model_name": "Qwen/Qwen3-8B",
                    "base_url": "http://127.0.0.1:8000/v1",
                    "api_key": "",
                }
            }
        ),
    )

    preprocess_model = resolve_model_config(settings, MODEL_ROUTE_PREPROCESS_GUARDRAILS)

    assert preprocess_model is not None
    assert preprocess_model.profile_name == "guardrails_local"


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


from __future__ import annotations

import json
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.model_selection import ModelPresetConfig, ModelProfileConfig


class Settings(BaseSettings):
    app_name: str = "Claread透读"
    app_env: str = "development"
    log_level: str = "INFO"
    analysis_model_name: str = ""
    analysis_base_url: str = ""
    analysis_api_key: str = ""
    guardrails_model_name: str = ""
    guardrails_base_url: str = ""
    guardrails_api_key: str = ""
    default_model_profile: str = ""
    preprocess_model_profile: str = ""
    core_model_profile: str = ""
    translation_model_profile: str = ""
    minimax_m27_model_name: str = "MiniMax-M2.7"
    minimax_m27_base_url: str = "https://api.minimax.io/v1"
    minimax_m27_api_key: str = ""
    model_profiles_json: str = ""
    model_presets_json: str = ""
    langsmith_enabled: bool = False
    langsmith_tracing: bool = True
    langsmith_project: str = "english-article-interpretation-dev"
    langsmith_api_key: str = ""
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_workspace_id: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def _load_custom_model_profiles(self) -> dict[str, ModelProfileConfig]:
        if not self.model_profiles_json.strip():
            return {}

        payload = json.loads(self.model_profiles_json)
        if not isinstance(payload, dict):
            raise ValueError("MODEL_PROFILES_JSON must be a JSON object keyed by profile name")

        profiles: dict[str, ModelProfileConfig] = {}
        for profile_name, profile_payload in payload.items():
            if not isinstance(profile_payload, dict):
                raise ValueError(f"MODEL_PROFILES_JSON[{profile_name!r}] must be a JSON object")
            profile = ModelProfileConfig.model_validate(profile_payload)
            if profile.is_configured():
                profiles[profile_name] = profile
        return profiles

    def model_profiles(self) -> dict[str, ModelProfileConfig]:
        profiles: dict[str, ModelProfileConfig] = {}

        legacy_analysis = ModelProfileConfig(
            model_name=self.analysis_model_name,
            base_url=self.analysis_base_url,
            api_key=self.analysis_api_key,
        )
        if legacy_analysis.is_configured():
            profiles["legacy_analysis"] = legacy_analysis

        legacy_guardrails = ModelProfileConfig(
            model_name=self.guardrails_model_name,
            base_url=self.guardrails_base_url,
            api_key=self.guardrails_api_key,
        )
        if legacy_guardrails.is_configured():
            profiles["legacy_guardrails"] = legacy_guardrails

        minimax_m27 = ModelProfileConfig(
            model_name=self.minimax_m27_model_name,
            base_url=self.minimax_m27_base_url,
            api_key=self.minimax_m27_api_key,
        )
        if minimax_m27.is_configured():
            profiles["minimax_m27"] = minimax_m27

        profiles.update(self._load_custom_model_profiles())
        return profiles

    def model_presets(self) -> dict[str, ModelPresetConfig]:
        if not self.model_presets_json.strip():
            return {}

        payload = json.loads(self.model_presets_json)
        if not isinstance(payload, dict):
            raise ValueError("MODEL_PRESETS_JSON must be a JSON object keyed by preset name")

        presets: dict[str, ModelPresetConfig] = {}
        for preset_name, preset_payload in payload.items():
            if not isinstance(preset_payload, dict):
                raise ValueError(f"MODEL_PRESETS_JSON[{preset_name!r}] must be a JSON object")
            presets[preset_name] = ModelPresetConfig.model_validate(preset_payload)
        return presets


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

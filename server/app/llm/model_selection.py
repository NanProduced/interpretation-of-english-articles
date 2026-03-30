from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai.settings import ModelSettings

MODEL_ROUTE_PREPROCESS_GUARDRAILS = "preprocess_guardrails"
MODEL_ROUTE_ANALYSIS_CORE = "analysis_core"
MODEL_ROUTE_ANALYSIS_TRANSLATION = "analysis_translation"

ModelRoute = Literal[
    "preprocess_guardrails",
    "analysis_core",
    "analysis_translation",
]


class RunModelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_tokens: int | None = Field(default=None, ge=1)
    temperature: float | None = Field(default=None, ge=0.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    timeout: float | None = Field(default=None, gt=0.0)
    parallel_tool_calls: bool | None = None
    seed: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    stop_sequences: list[str] | None = None
    extra_headers: dict[str, str] | None = None
    extra_body: dict[str, object] | None = None

    def merged_with(self, override: RunModelSettings | None) -> RunModelSettings:
        if override is None:
            return self.model_copy(deep=True)
        merged = self.model_dump(exclude_none=True)
        merged.update(override.model_dump(exclude_none=True))
        return RunModelSettings.model_validate(merged)

    def to_pydantic_ai(self) -> ModelSettings | None:
        payload = self.model_dump(exclude_none=True)
        if not payload:
            return None
        return ModelSettings(**payload)


class ModelProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str = ""
    base_url: str = ""
    api_key: str = ""
    model_settings: RunModelSettings | None = None

    def is_configured(self) -> bool:
        return bool(self.model_name and self.base_url)


class RouteModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str | None = None
    fallback_profiles: list[str] = Field(default_factory=list)
    model_settings: RunModelSettings | None = None


class ModelSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset: str | None = None
    default_profile: str | None = None
    routes: dict[ModelRoute, RouteModelSelection] = Field(default_factory=dict)


class ModelPresetConfig(ModelSelection):
    pass


def parse_model_selection(raw: object) -> ModelSelection | None:
    if raw is None:
        return None
    if isinstance(raw, ModelSelection):
        return raw
    if isinstance(raw, dict) and not raw:
        return None
    return ModelSelection.model_validate(raw)

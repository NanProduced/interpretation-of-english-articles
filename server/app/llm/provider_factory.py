from __future__ import annotations

from collections.abc import Callable

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.llm.types import ResolvedModelConfig


class ModelProviderError(ValueError):
    """Raised when a configured provider cannot be built."""


def _build_openai_compatible_model(model_config: ResolvedModelConfig) -> OpenAIChatModel | None:
    if not model_config.model_name or not model_config.base_url:
        return None

    provider = OpenAIProvider(
        base_url=model_config.base_url,
        api_key=model_config.api_key or None,
    )
    return OpenAIChatModel(
        model_config.model_name,
        provider=provider,
        settings=model_config.model_settings.to_pydantic_ai() if model_config.model_settings else None,
    )


PROVIDER_BUILDERS: dict[str, Callable[[ResolvedModelConfig], object | None]] = {
    "openai_compatible": _build_openai_compatible_model,
}


def build_model_instance(model_config: ResolvedModelConfig):
    builder = PROVIDER_BUILDERS.get(model_config.provider)
    if builder is None:
        raise ModelProviderError(f"Unsupported model provider: {model_config.provider}")
    return builder(model_config)


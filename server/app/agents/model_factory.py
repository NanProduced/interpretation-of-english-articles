from __future__ import annotations

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config.settings import Settings


def build_openai_compatible_model(
    *,
    model_name: str,
    base_url: str,
    api_key: str,
) -> OpenAIChatModel | None:
    if not model_name or not base_url:
        return None

    # 统一封装 OpenAI-compatible 模型构造，避免各个 agent 重复处理 base_url / api_key。
    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key or None,
    )
    return OpenAIChatModel(model_name, provider=provider)


def build_analysis_model(settings: Settings) -> OpenAIChatModel | None:
    # 当前优先读 ANALYSIS_*，如果没配，再复用已有的 GUARDRAILS_* 配置，方便本地先复用同一个 vLLM。
    return build_openai_compatible_model(
        model_name=settings.analysis_model_name or settings.guardrails_model_name,
        base_url=settings.analysis_base_url or settings.guardrails_base_url,
        api_key=settings.analysis_api_key or settings.guardrails_api_key,
    )


def build_guardrails_model(settings: Settings) -> OpenAIChatModel | None:
    return build_openai_compatible_model(
        model_name=settings.guardrails_model_name,
        base_url=settings.guardrails_base_url,
        api_key=settings.guardrails_api_key,
    )

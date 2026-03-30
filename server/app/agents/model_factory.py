from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config.settings import Settings
from app.llm.model_selection import (
    MODEL_ROUTE_ANALYSIS_CORE,
    MODEL_ROUTE_ANALYSIS_TRANSLATION,
    MODEL_ROUTE_PREPROCESS_GUARDRAILS,
    ModelRoute,
    ModelSelection,
    RouteModelSelection,
    RunModelSettings,
)


class ModelSelectionError(ValueError):
    """Raised when runtime model routing references an unknown preset or profile."""


class ResolvedModelConfig(BaseModel):
    route: ModelRoute
    profile_name: str
    model_name: str
    base_url: str
    api_key: str
    fallback_profiles: list[str] = Field(default_factory=list)
    model_settings: RunModelSettings | None = None

    def cache_key(self) -> str:
        return self.model_dump_json(exclude_none=True)


def build_openai_compatible_model(
    *,
    model_name: str,
    base_url: str,
    api_key: str,
    model_settings: RunModelSettings | None = None,
) -> OpenAIChatModel | None:
    if not model_name or not base_url:
        return None

    provider = OpenAIProvider(
        base_url=base_url,
        api_key=api_key or None,
    )
    return OpenAIChatModel(
        model_name,
        provider=provider,
        settings=model_settings.to_pydantic_ai() if model_settings else None,
    )


def _selected_profile_name(settings: Settings, route: ModelRoute) -> str:
    route_profile_map = {
        MODEL_ROUTE_PREPROCESS_GUARDRAILS: settings.preprocess_model_profile,
        MODEL_ROUTE_ANALYSIS_CORE: settings.core_model_profile,
        MODEL_ROUTE_ANALYSIS_TRANSLATION: settings.translation_model_profile,
    }
    return route_profile_map[route] or settings.default_model_profile


def _load_preset(settings: Settings, selection: ModelSelection | None):
    if selection is None or not selection.preset:
        return None

    preset = settings.model_presets().get(selection.preset)
    if preset is None:
        raise ModelSelectionError(f"Unknown model preset: {selection.preset}")
    return preset


def _route_override(selection: ModelSelection | None, route: ModelRoute) -> RouteModelSelection | None:
    if selection is None:
        return None
    return selection.routes.get(route)


def _resolve_profile_name(
    settings: Settings,
    route: ModelRoute,
    selection: ModelSelection | None,
) -> tuple[str | None, RouteModelSelection | None, RouteModelSelection | None]:
    preset = _load_preset(settings, selection)
    preset_route = preset.routes.get(route) if preset else None
    route_override = _route_override(selection, route)

    if route_override and route_override.profile:
        return route_override.profile, preset_route, route_override

    if preset_route and preset_route.profile:
        return preset_route.profile, preset_route, route_override

    if selection and selection.default_profile:
        return selection.default_profile, preset_route, route_override

    if preset and preset.default_profile:
        return preset.default_profile, preset_route, route_override

    deployment_default = _selected_profile_name(settings, route)
    return deployment_default or None, preset_route, route_override


def _resolve_fallback_profiles(
    preset_route: RouteModelSelection | None,
    route_override: RouteModelSelection | None,
) -> list[str]:
    if route_override and "fallback_profiles" in route_override.model_fields_set:
        return list(route_override.fallback_profiles)
    if preset_route and "fallback_profiles" in preset_route.model_fields_set:
        return list(preset_route.fallback_profiles)
    return []


def _resolve_route_settings(
    profile_settings: RunModelSettings | None,
    preset_route: RouteModelSelection | None,
    route_override: RouteModelSelection | None,
) -> RunModelSettings | None:
    settings_chain = profile_settings
    if preset_route and preset_route.model_settings is not None:
        settings_chain = (
            preset_route.model_settings
            if settings_chain is None
            else settings_chain.merged_with(preset_route.model_settings)
        )
    if route_override and route_override.model_settings is not None:
        settings_chain = (
            route_override.model_settings
            if settings_chain is None
            else settings_chain.merged_with(route_override.model_settings)
        )
    return settings_chain


def _build_legacy_model_config(settings: Settings, route: ModelRoute) -> ResolvedModelConfig | None:
    if route == MODEL_ROUTE_PREPROCESS_GUARDRAILS:
        if not settings.guardrails_model_name or not settings.guardrails_base_url:
            return None
        return ResolvedModelConfig(
            route=route,
            profile_name="legacy_guardrails",
            model_name=settings.guardrails_model_name,
            base_url=settings.guardrails_base_url,
            api_key=settings.guardrails_api_key,
        )

    model_name = settings.analysis_model_name or settings.guardrails_model_name
    base_url = settings.analysis_base_url or settings.guardrails_base_url
    api_key = settings.analysis_api_key or settings.guardrails_api_key
    if not model_name or not base_url:
        return None

    return ResolvedModelConfig(
        route=route,
        profile_name="legacy_analysis",
        model_name=model_name,
        base_url=base_url,
        api_key=api_key,
    )


def resolve_model_config(
    settings: Settings,
    route: ModelRoute,
    selection: ModelSelection | None = None,
) -> ResolvedModelConfig | None:
    profile_name, preset_route, route_override = _resolve_profile_name(settings, route, selection)
    if profile_name:
        profile = settings.model_profiles().get(profile_name)
        if profile is None:
            raise ModelSelectionError(f"Unknown model profile for {route}: {profile_name}")
        if profile.is_configured():
            return ResolvedModelConfig(
                route=route,
                profile_name=profile_name,
                model_name=profile.model_name,
                base_url=profile.base_url,
                api_key=profile.api_key,
                fallback_profiles=_resolve_fallback_profiles(preset_route, route_override),
                model_settings=_resolve_route_settings(profile.model_settings, preset_route, route_override),
            )

    return _build_legacy_model_config(settings, route)


def validate_model_selection(
    settings: Settings,
    selection: ModelSelection | None,
    routes: tuple[ModelRoute, ...],
) -> None:
    if selection is None:
        return
    for route in routes:
        resolve_model_config(settings, route, selection)

def build_model_for_route(
    settings: Settings,
    route: ModelRoute,
    selection: ModelSelection | None = None,
):
    model_config = resolve_model_config(settings, route, selection)
    if model_config is None:
        return None, None

    primary_model = build_openai_compatible_model(
        model_name=model_config.model_name,
        base_url=model_config.base_url,
        api_key=model_config.api_key,
        model_settings=model_config.model_settings,
    )
    if primary_model is None:
        return None, model_config

    if not model_config.fallback_profiles:
        return primary_model, model_config

    fallback_models = []
    profiles = settings.model_profiles()
    for fallback_profile_name in model_config.fallback_profiles:
        fallback_profile = profiles.get(fallback_profile_name)
        if fallback_profile is None:
            raise ModelSelectionError(
                f"Unknown fallback model profile for {route}: {fallback_profile_name}"
            )
        fallback_model = build_openai_compatible_model(
            model_name=fallback_profile.model_name,
            base_url=fallback_profile.base_url,
            api_key=fallback_profile.api_key,
            model_settings=model_config.model_settings or fallback_profile.model_settings,
        )
        if fallback_model is not None:
            fallback_models.append(fallback_model)

    if not fallback_models:
        return primary_model, model_config

    return FallbackModel(primary_model, *fallback_models), model_config

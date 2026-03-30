from __future__ import annotations

from app.agents.core_v0 import CoreAgentDeps, build_core_prompt, get_core_agent
from app.agents.translation_v0 import (
    TranslationAgentDeps,
    build_translation_prompt,
    get_translation_agent,
)
from app.llm.agent_runner import run_agent_with_route
from app.llm.routes import MODEL_ROUTE_ANALYSIS_CORE, MODEL_ROUTE_ANALYSIS_TRANSLATION
from app.llm.types import ModelSelection
from app.schemas.internal.analysis import CoreAgentOutput, TranslationAgentOutput


async def run_core_agent_raw(
    deps: CoreAgentDeps,
    model_selection: ModelSelection | None = None,
):
    return await run_agent_with_route(
        agent=get_core_agent(),
        prompt=build_core_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANALYSIS_CORE,
        model_selection=model_selection,
    )


async def run_core_agent(
    deps: CoreAgentDeps,
    model_selection: ModelSelection | None = None,
) -> CoreAgentOutput:
    result = await run_core_agent_raw(deps, model_selection=model_selection)
    return result.output


async def run_translation_agent_raw(
    deps: TranslationAgentDeps,
    model_selection: ModelSelection | None = None,
):
    return await run_agent_with_route(
        agent=get_translation_agent(),
        prompt=build_translation_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANALYSIS_TRANSLATION,
        model_selection=model_selection,
    )


async def run_translation_agent(
    deps: TranslationAgentDeps,
    model_selection: ModelSelection | None = None,
) -> TranslationAgentOutput:
    result = await run_translation_agent_raw(deps, model_selection=model_selection)
    return result.output


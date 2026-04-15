from __future__ import annotations

from typing import Any

from app.agents.academic_translation_agent import (
    AcademicTranslationAgentDeps,
    build_academic_translation_prompt,
    get_academic_translation_agent,
)
from app.agents.interpretation_agent import (
    InterpretationAgentDeps,
    build_interpretation_prompt,
    get_interpretation_agent,
)
from app.agents.logic_agent import (
    LogicAgentDeps,
    build_logic_prompt,
    get_logic_agent,
)
from app.agents.structure_agent import (
    StructureAgentDeps,
    build_structure_prompt,
    get_structure_agent,
)
from app.agents.term_agent import (
    TermAgentDeps,
    build_term_prompt,
    get_term_agent,
)
from app.llm.agent_runner import run_agent_with_route
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.types import ModelSelection


async def run_term_agent(
    deps: TermAgentDeps,
    model_selection: ModelSelection | None = None,
) -> Any:
    return await run_agent_with_route(
        agent=get_term_agent(),
        prompt=build_term_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=model_selection,
    )


async def run_logic_agent(
    deps: LogicAgentDeps,
    model_selection: ModelSelection | None = None,
) -> Any:
    return await run_agent_with_route(
        agent=get_logic_agent(),
        prompt=build_logic_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=model_selection,
    )


async def run_interpretation_agent(
    deps: InterpretationAgentDeps,
    model_selection: ModelSelection | None = None,
) -> Any:
    return await run_agent_with_route(
        agent=get_interpretation_agent(),
        prompt=build_interpretation_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=model_selection,
    )


async def run_structure_agent(
    deps: StructureAgentDeps,
    model_selection: ModelSelection | None = None,
) -> Any:
    return await run_agent_with_route(
        agent=get_structure_agent(),
        prompt=build_structure_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=model_selection,
    )


async def run_academic_translation_agent(
    deps: AcademicTranslationAgentDeps,
    model_selection: ModelSelection | None = None,
) -> Any:
    return await run_agent_with_route(
        agent=get_academic_translation_agent(),
        prompt=build_academic_translation_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=model_selection,
    )

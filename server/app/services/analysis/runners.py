from __future__ import annotations

from typing import Any

from app.agents.annotation import AnnotationAgentDeps, build_annotation_prompt, get_annotation_agent
from app.llm.agent_runner import run_agent_with_route
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.types import ModelSelection


async def run_annotation_agent(
    deps: AnnotationAgentDeps,
    model_selection: ModelSelection | None = None,
) -> Any:
    return await run_agent_with_route(
        agent=get_annotation_agent(),
        prompt=build_annotation_prompt(deps),
        deps=deps,
        route=MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=model_selection,
    )

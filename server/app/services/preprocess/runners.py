from __future__ import annotations

from app.agents.preprocess_v0 import GuardrailsDeps, get_guardrails_agent
from app.llm.agent_runner import run_agent_with_route
from app.llm.routes import MODEL_ROUTE_PREPROCESS_GUARDRAILS
from app.llm.types import ModelSelection


async def run_guardrails_agent(
    clean_text: str,
    deps: GuardrailsDeps,
    model_selection: ModelSelection | None = None,
):
    return await run_agent_with_route(
        agent=get_guardrails_agent(),
        prompt=clean_text,
        deps=deps,
        route=MODEL_ROUTE_PREPROCESS_GUARDRAILS,
        model_selection=model_selection,
    )


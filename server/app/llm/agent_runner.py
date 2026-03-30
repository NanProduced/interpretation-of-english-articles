from __future__ import annotations

from typing import Any

from app.config.settings import get_settings
from app.llm.router import build_model_for_route
from app.llm.routes import ModelRoute
from app.llm.types import ModelSelection


async def run_agent_with_route(
    *,
    agent,
    prompt: str,
    deps: Any,
    route: ModelRoute,
    model_selection: ModelSelection | None = None,
):
    model, _ = build_model_for_route(get_settings(), route, model_selection)
    if model is None:
        raise RuntimeError(f"model route is not configured: {route}")
    return await agent.run(prompt, deps=deps, model=model)


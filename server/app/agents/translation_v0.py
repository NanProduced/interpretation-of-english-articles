from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, AgentRunResult, RunContext

from app.agents.model_factory import MODEL_ROUTE_ANALYSIS_TRANSLATION, build_model_for_route
from app.config.settings import get_settings
from app.llm.model_selection import ModelSelection
from app.schemas.analysis import TranslationAgentOutput


@dataclass
class TranslationAgentDeps:
    profile_key: str
    render_text: str
    sentences: list[dict[str, object]]


def _instructions(ctx: RunContext[TranslationAgentDeps]) -> str:
    deps = ctx.deps
    return f"""
You are translation_agent_v0 in an English article interpretation workflow.

Return structured JSON for:
1. sentence_translations
2. full_translation_zh
3. key_phrase_translations

User profile:
- profile_key: {deps.profile_key}

Rules:
1. Output must match TranslationAgentOutput exactly.
2. sentence_translations must cover every input sentence_id.
3. key_phrase_translations should stay selective and useful.
4. key_phrase_translations spans must use render_text offsets.
5. style must be one of: natural, exam, literal.
6. Keep translations concise and readable.
7. Do not output markdown or extra commentary.
""".strip()


def _prompt(deps: TranslationAgentDeps) -> str:
    return json.dumps(
        {
            "render_text": deps.render_text,
            "sentences": deps.sentences,
        },
        ensure_ascii=False,
    )


@lru_cache(maxsize=1)
def get_translation_agent() -> Agent[TranslationAgentDeps, TranslationAgentOutput]:
    return Agent[TranslationAgentDeps, TranslationAgentOutput](
        model=None,
        output_type=TranslationAgentOutput,
        deps_type=TranslationAgentDeps,
        instructions=_instructions,
        name="translation_agent_v0",
        retries=2,
        output_retries=2,
        instrument=False,
    )


async def run_translation_agent_raw(
    deps: TranslationAgentDeps,
    model_selection: ModelSelection | None = None,
) -> AgentRunResult[TranslationAgentOutput]:
    agent = get_translation_agent()
    model, _ = build_model_for_route(get_settings(), MODEL_ROUTE_ANALYSIS_TRANSLATION, model_selection)
    if model is None:
        raise RuntimeError("analysis model is not configured")

    return await agent.run(_prompt(deps), deps=deps, model=model)


async def run_translation_agent(
    deps: TranslationAgentDeps,
    model_selection: ModelSelection | None = None,
) -> TranslationAgentOutput:
    result = await run_translation_agent_raw(deps, model_selection=model_selection)
    return result.output

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, AgentRunResult, RunContext

from app.agents.model_factory import build_analysis_model
from app.config.settings import get_settings
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
    # translation_agent 只关心正文和句子结构，不重复处理 profile 之外的上下文。
    return json.dumps(
        {
            "render_text": deps.render_text,
            "sentences": deps.sentences,
        },
        ensure_ascii=False,
    )


@lru_cache(maxsize=1)
def get_translation_agent() -> Agent[TranslationAgentDeps, TranslationAgentOutput] | None:
    model = build_analysis_model(get_settings())
    if model is None:
        return None

    # 翻译拆成独立 agent，便于后续单独优化 prompt、模型和降级策略。
    return Agent[TranslationAgentDeps, TranslationAgentOutput](
        model=model,
        output_type=TranslationAgentOutput,
        deps_type=TranslationAgentDeps,
        instructions=_instructions,
        name="translation_agent_v0",
        retries=2,
        output_retries=2,
        # tracing 统一由 workflow 层控制，避免 agent 自己生成并列 root trace。
        instrument=False,
    )


async def run_translation_agent_raw(deps: TranslationAgentDeps) -> AgentRunResult[TranslationAgentOutput]:
    agent = get_translation_agent()
    if agent is None:
        raise RuntimeError("analysis model is not configured")

    return await agent.run(_prompt(deps), deps=deps)


async def run_translation_agent(deps: TranslationAgentDeps) -> TranslationAgentOutput:
    result = await run_translation_agent_raw(deps)
    return result.output

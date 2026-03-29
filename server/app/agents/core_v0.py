from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, AgentRunResult, RunContext

from app.agents.model_factory import build_analysis_model
from app.config.settings import get_settings
from app.schemas.analysis import CoreAgentOutput


@dataclass
class CoreAgentDeps:
    profile_key: str
    sentences: list[dict[str, object]]


def _instructions(ctx: RunContext[CoreAgentDeps]) -> str:
    deps = ctx.deps
    return f"""
You are core_agent_v0 in an English article interpretation workflow.

Your job is to return structured JSON for:
1. vocabulary
2. grammar
3. difficult_sentences

User profile:
- profile_key: {deps.profile_key}

Rules:
1. Output must match CoreAgentOutput exactly.
2. Every annotation must reference an existing sentence_id.
3. Every span must use the absolute start/end offsets already provided in the sentences.
4. Vocabulary must only include priority words or short phrases, not every word.
5. Grammar must focus on high-value grammar points or sentence components.
6. difficult_sentences must only include truly difficult sentences.
7. objective_level must be one of: basic, intermediate, advanced.
8. grammar.type must be one of: grammar_point, sentence_component, error_flag.
9. sentence_component.label must be one of: subject, predicate, object, complement, modifier, adverbial, clause.
10. Keep each Chinese explanation concise.
11. Keep output small and useful:
   - vocabulary: at most 8 items
   - grammar: at most 8 items
   - difficult_sentences: at most 3 items
12. Do not output markdown or extra commentary.
""".strip()


def _prompt(deps: CoreAgentDeps) -> str:
    # 显式传入 sentence_id 和 span，降低结构化结果回填前端时的歧义。
    return json.dumps(
        {
            "sentences": deps.sentences,
        },
        ensure_ascii=False,
    )


@lru_cache(maxsize=1)
def get_core_agent() -> Agent[CoreAgentDeps, CoreAgentOutput] | None:
    model = build_analysis_model(get_settings())
    if model is None:
        return None

    # core_agent 只负责词汇、语法、长难句三类强耦合任务。
    return Agent[CoreAgentDeps, CoreAgentOutput](
        model=model,
        output_type=CoreAgentOutput,
        deps_type=CoreAgentDeps,
        instructions=_instructions,
        name="core_agent_v0",
        retries=2,
        output_retries=2,
        # tracing 统一由 workflow 层控制，避免 agent 自己生成并列 root trace。
        instrument=False,
    )


async def run_core_agent_raw(deps: CoreAgentDeps) -> AgentRunResult[CoreAgentOutput]:
    agent = get_core_agent()
    if agent is None:
        raise RuntimeError("analysis model is not configured")

    return await agent.run(_prompt(deps), deps=deps)


async def run_core_agent(deps: CoreAgentDeps) -> CoreAgentOutput:
    result = await run_core_agent_raw(deps)
    return result.output

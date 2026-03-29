from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, RunContext

from app.agents.model_factory import build_analysis_model
from app.config.settings import get_settings
from app.schemas.analysis import CoreAgentOutput


@dataclass
class CoreAgentDeps:
    profile_key: str
    render_text: str
    paragraphs: list[dict[str, object]]
    sentences: list[dict[str, object]]


def _instructions(ctx: RunContext[CoreAgentDeps]) -> str:
    deps = ctx.deps
    return f"""
你是英文文章解读工作流中的 core_agent_v0。

你的职责是基于文章文本和句子切分结果，输出完整且结构化的三类分析：
1. 重点词汇标注 vocabulary
2. 语法标注 grammar
3. 长难句拆解 difficult_sentences

用户 profile:
- profile_key: {deps.profile_key}

约束:
1. 只输出 CoreAgentOutput 对应结构。
2. 所有 annotation 都必须引用现有 sentence_id。
3. 所有 span 都必须基于 render_text。
4. vocabulary 只标重点词和重点短语，不要给全文每个词做标注。
5. grammar 至少覆盖关键语法点或句子成分，不要输出空泛结论。
6. difficult_sentences 只保留真正有阅读阻力的句子。
7. priority 只能是 core / expand / reference。
8. objective_level 只能是 basic / intermediate / advanced。
9. grammar.type 只能是 grammar_point / sentence_component / error_flag。
10. sentence_component 的 label 只能是 subject / predicate / object / complement / modifier / adverbial / clause。
11. 不要输出 markdown，不要附加解释，不要输出思考过程。
""".strip()


def _prompt(deps: CoreAgentDeps) -> str:
    # 这里显式传 sentence_id 和 span，目的是让模型输出能稳定落回前端可渲染结构。
    return json.dumps(
        {
            "render_text": deps.render_text,
            "paragraphs": deps.paragraphs,
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
        instrument=True,
    )


async def run_core_agent(deps: CoreAgentDeps) -> CoreAgentOutput:
    agent = get_core_agent()
    if agent is None:
        raise RuntimeError("analysis model is not configured")

    # metadata 会进入 LangSmith，后续对比不同版本 prompt / 模型时会直接依赖这些字段。
    result = await agent.run(
        _prompt(deps),
        deps=deps,
        metadata={
            "node": "core_agent_v0",
            "workflow_version": "analyze_v0",
            "schema_version": "0.1.0",
            "profile_key": deps.profile_key,
        },
    )
    return result.output

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, RunContext

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
你是英文文章解读工作流中的 translation_agent_v0。

你的职责是输出：
1. 逐句翻译 sentence_translations
2. 全文翻译 full_translation_zh
3. 关键短语翻译 key_phrase_translations

用户 profile:
- profile_key: {deps.profile_key}

约束:
1. 只输出 TranslationAgentOutput 对应结构。
2. sentence_translations 必须覆盖输入中的每一个 sentence_id。
3. key_phrase_translations 只保留最值得单独解释的短语，不要过量输出。
4. key_phrase_translations 的 span 必须基于 render_text。
5. style 只能是 natural / exam / literal。
6. 不要输出 markdown，不要附加解释，不要输出思考过程。
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

    # 翻译单独拆成一个 agent，后面便于独立调 prompt、做并行和降级。
    return Agent[TranslationAgentDeps, TranslationAgentOutput](
        model=model,
        output_type=TranslationAgentOutput,
        deps_type=TranslationAgentDeps,
        instructions=_instructions,
        name="translation_agent_v0",
        retries=2,
        output_retries=2,
        instrument=True,
    )


async def run_translation_agent(deps: TranslationAgentDeps) -> TranslationAgentOutput:
    agent = get_translation_agent()
    if agent is None:
        raise RuntimeError("analysis model is not configured")

    result = await agent.run(
        _prompt(deps),
        deps=deps,
        metadata={
            "node": "translation_agent_v0",
            "workflow_version": "analyze_v0",
            "schema_version": "0.1.0",
            "profile_key": deps.profile_key,
        },
    )
    return result.output

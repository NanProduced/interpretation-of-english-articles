from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, AgentRunResult, RunContext

from app.agents.model_factory import MODEL_ROUTE_ANALYSIS_CORE, build_model_for_route
from app.config.settings import get_settings
from app.llm.model_selection import ModelSelection
from app.schemas.analysis import CoreAgentOutput


@dataclass
class CoreAgentDeps:
    profile_key: str
    sentences: list[dict[str, object]]


def _instructions(ctx: RunContext[CoreAgentDeps]) -> str:
    deps = ctx.deps
    return f"""
您是英文文章解释工作流程中的 core_agent_v0。

您的工作是返回结构化 JSON：
1.词汇
2.语法
3.长难句

用户配置:
- profile_key: {deps.profile_key}

规则:
1. 输出必须与CoreAgentOutput 完全匹配。
2. 每个注释必须引用现有的sentence_id。
3. 每个跨度必须使用句子中已提供的绝对开始/结束偏移量。
4. 词汇只能包含优先单词或短语，而不是每个单词。
5.语法必须关注高价值的语法点或句子成分。
6.困难句子必须只包括真正困难的句子。
7. Objective_level 必须是以下之一：基础、中级、高级。
8. Grammar.type 必须是以下之一：grammar_point、sentence_component、error_flag。
9. Sentence_Component.label 必须是以下之一：主语、谓语、宾语、补语、修饰语、状语、从句。
10. 保持每个中文解释的简洁。
11. 保持输出小而有用：
   - 词汇：最多8个项目
   - 语法：最多8项
   - 困难句子：最多 3 条
12.不要输出markdown或额外的评论。
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
def get_core_agent() -> Agent[CoreAgentDeps, CoreAgentOutput]:
    # Agent 蓝图与模型解耦，真正的模型在 run 时按当前请求路由注入。
    return Agent[CoreAgentDeps, CoreAgentOutput](
        model=None,
        output_type=CoreAgentOutput,
        deps_type=CoreAgentDeps,
        instructions=_instructions,
        name="core_agent_v0",
        retries=2,
        output_retries=2,
        instrument=False,
    )


async def run_core_agent_raw(
    deps: CoreAgentDeps,
    model_selection: ModelSelection | None = None,
) -> AgentRunResult[CoreAgentOutput]:
    agent = get_core_agent()
    model, _ = build_model_for_route(get_settings(), MODEL_ROUTE_ANALYSIS_CORE, model_selection)
    if model is None:
        raise RuntimeError("analysis model is not configured")

    return await agent.run(_prompt(deps), deps=deps, model=model)


async def run_core_agent(deps: CoreAgentDeps, model_selection: ModelSelection | None = None) -> CoreAgentOutput:
    result = await run_core_agent_raw(deps, model_selection=model_selection)
    return result.output

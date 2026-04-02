"""V3 article_analysis workflow 入口。

v3 流程：
START → prepare_input → derive_user_config
    → [并行: parallel_agents (vocabulary + grammar + translation)]
    → normalize_and_ground
    → [条件: repair_agent]
    → project_render_scene
    → assemble_result → END
"""

from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.config.settings import get_settings
from app.llm.router import resolve_model_config, validate_model_selection
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.runtime import dump_model_selection
from app.llm.types import ModelSelection, parse_model_selection
from app.schemas.analysis import AnalyzeRequest, RenderSceneModel
from app.services.analysis.user_rules import derive_user_rules
from app.workflow.analyze_nodes import (
    WORKFLOW_NAME,
    WORKFLOW_VERSION,
    assemble_result_node,
    derive_user_config_node,
    grammar_agent_node,
    normalize_and_ground_node,
    parallel_agents_node,
    prepare_input_node,
    project_render_scene_node,
    repair_agent_node,
    translation_agent_node,
    vocabulary_agent_node,
)
from app.workflow.analyze_state import AnalyzeState
from app.workflow.tracing import build_workflow_root_metadata, build_workflow_root_tags

ANALYZE_SCHEMA_VERSION = "3.0.0"


def _collect_model_names(settings: Any, model_selection: ModelSelection | None) -> list[str]:
    model_config = resolve_model_config(
        settings,
        MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection,
    )
    if model_config and model_config.model_name:
        return [model_config.model_name]
    return []


def _should_repair(state: AnalyzeState) -> bool:
    """判断是否需要触发 repair_agent。"""
    normalized_result = state.get("normalized_result")
    if normalized_result is None:
        return False

    drop_count = len(normalized_result.drop_log) if normalized_result.drop_log else 0
    annotation_count = len(normalized_result.annotations)

    if annotation_count == 0:
        return drop_count > 0

    failure_ratio = drop_count / (annotation_count + drop_count)
    return failure_ratio > 0.20


def build_article_analysis_graph() -> Any:
    graph = StateGraph(AnalyzeState)

    # 基础节点
    graph.add_node("prepare_input", prepare_input_node)
    graph.add_node("derive_user_config", derive_user_config_node)

    # 并行 agent 节点（单一入口，避免重复调用）
    graph.add_node("parallel_agents", parallel_agents_node)
    # 保留三个 agent 节点作为空壳（兼容旧接口）
    graph.add_node("vocabulary_agent", vocabulary_agent_node)
    graph.add_node("grammar_agent", grammar_agent_node)
    graph.add_node("translation_agent", translation_agent_node)

    # 归一化节点
    graph.add_node("normalize_and_ground", normalize_and_ground_node)

    # 可选 repair 节点
    graph.add_node("repair_agent", repair_agent_node)

    # 投影和结果收敛
    graph.add_node("project_render_scene", project_render_scene_node)
    graph.add_node("assemble_result", assemble_result_node)

    # 边连接
    graph.add_edge(START, "prepare_input")
    graph.add_edge("prepare_input", "derive_user_config")

    # 并行 agent 执行（在 derive_user_config 之后，单一入口）
    graph.add_edge("derive_user_config", "parallel_agents")

    # 归一化（在并行 agent 完成之后）
    graph.add_edge("parallel_agents", "normalize_and_ground")

    # Repair（条件触发）
    graph.add_conditional_edges(
        "normalize_and_ground",
        _should_repair,
        {
            True: "repair_agent",
            False: "project_render_scene",
        },
    )

    # Repair 之后继续投影
    graph.add_edge("repair_agent", "project_render_scene")

    # 最终结果收敛
    graph.add_edge("project_render_scene", "assemble_result")
    graph.add_edge("assemble_result", END)

    return graph.compile()


async def _invoke_article_analysis(payload: AnalyzeRequest) -> dict[str, Any]:
    graph = build_article_analysis_graph()
    request_id = payload.request_id or str(uuid4())
    normalized_payload = (
        payload
        if payload.request_id
        else payload.model_copy(update={"request_id": request_id})
    )
    model_selection = parse_model_selection(normalized_payload.model_selection)
    validate_model_selection(
        get_settings(),
        model_selection,
        (MODEL_ROUTE_ANNOTATION_GENERATION,),
    )
    user_rules = derive_user_rules(
        normalized_payload.reading_goal,
        normalized_payload.reading_variant,
    )
    settings = get_settings()
    model_names = _collect_model_names(settings, model_selection)
    result = await graph.ainvoke(
        {"payload": normalized_payload},
        config={
            "run_name": WORKFLOW_NAME,
            "tags": build_workflow_root_tags(WORKFLOW_NAME, model_names),
            "configurable": {
                "model_selection": dump_model_selection(model_selection),
            },
            "metadata": build_workflow_root_metadata(
                workflow_name=WORKFLOW_NAME,
                workflow_version=WORKFLOW_VERSION,
                schema_version=ANALYZE_SCHEMA_VERSION,
                request_id=request_id,
                source_type=normalized_payload.source_type,
                reading_goal=normalized_payload.reading_goal,
                reading_variant=normalized_payload.reading_variant,
                profile_id=user_rules.profile_id,
                extra={
                    "model_preset": model_selection.preset if model_selection else None,
                    "runtime_model_selection": bool(model_selection),
                },
            ),
        },
    )
    return cast(dict[str, Any], result)


async def run_article_analysis(payload: AnalyzeRequest) -> RenderSceneModel:
    result = await _invoke_article_analysis(payload)
    return cast(RenderSceneModel, result["render_scene"])


async def run_article_analysis_with_state(payload: AnalyzeRequest) -> dict[str, Any]:
    return await _invoke_article_analysis(payload)


__all__ = [
    "ANALYZE_SCHEMA_VERSION",
    "WORKFLOW_NAME",
    "WORKFLOW_VERSION",
    "build_article_analysis_graph",
    "run_article_analysis",
    "run_article_analysis_with_state",
]

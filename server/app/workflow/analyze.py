"""analyze workflow 入口。

这个文件只保留 graph 装配和对外入口，避免把 helper、node、fallback 和 tracing 细节继续堆在一起。
"""

from __future__ import annotations

from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.workflow.analyze_nodes import (
    core_node,
    enrich_node,
    finalize_rejected_node,
    finalize_success_node,
    merge_node,
    preprocess_node,
    route_after_router,
    router_node,
    translation_node,
    validate_node,
)
from app.workflow.analyze_state import AnalyzeState
from app.workflow.tracing import build_workflow_root_metadata, build_workflow_root_tags


ANALYZE_SCHEMA_VERSION = "0.1.0"
ANALYZE_WORKFLOW_VERSION = "analyze_v0"
ANALYZE_TRACE_SCOPE = "analyze_local_debug"
ANALYZE_SAMPLE_BUCKET = "ad_hoc_local"


def build_analyze_graph():
    """构建 analyze v0 的 LangGraph。"""
    graph = StateGraph(AnalyzeState)
    graph.add_node("preprocess", preprocess_node)
    graph.add_node("router", router_node)
    graph.add_node("core", core_node)
    graph.add_node("translation", translation_node)
    graph.add_node("merge", merge_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("validate", validate_node)
    graph.add_node("finalize_success", finalize_success_node)
    graph.add_node("finalize_rejected", finalize_rejected_node)

    graph.add_edge(START, "preprocess")
    graph.add_edge("preprocess", "router")
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "core": "core",
            "rejected": "finalize_rejected",
        },
    )
    graph.add_edge("core", "translation")
    graph.add_edge("translation", "merge")
    graph.add_edge("merge", "enrich")
    graph.add_edge("enrich", "validate")
    graph.add_edge("validate", "finalize_success")
    graph.add_edge("finalize_success", END)
    graph.add_edge("finalize_rejected", END)
    return graph.compile()


async def run_analyze_v0(payload: AnalyzeRequest) -> AnalysisResult:
    """执行 analyze v0，并使用和 preprocess 一致的顶层 tracing 规范。"""
    graph = build_analyze_graph()
    request_id = payload.request_id or str(uuid4())
    normalized_payload = payload if payload.request_id else payload.model_copy(update={"request_id": request_id})
    result = await graph.ainvoke(
        {"payload": normalized_payload},
        config={
            "run_name": ANALYZE_WORKFLOW_VERSION,
            "tags": build_workflow_root_tags(ANALYZE_WORKFLOW_VERSION),
            "metadata": build_workflow_root_metadata(
                workflow_version=ANALYZE_WORKFLOW_VERSION,
                schema_version=ANALYZE_SCHEMA_VERSION,
                request_id=request_id,
                profile_key=normalized_payload.profile_key,
                source_type=normalized_payload.source_type,
                trace_scope=ANALYZE_TRACE_SCOPE,
                sample_bucket=ANALYZE_SAMPLE_BUCKET,
                extra={"discourse_enabled": normalized_payload.discourse_enabled},
            ),
        },
    )
    return result["result"]


__all__ = [
    "ANALYZE_SAMPLE_BUCKET",
    "ANALYZE_SCHEMA_VERSION",
    "ANALYZE_TRACE_SCOPE",
    "ANALYZE_WORKFLOW_VERSION",
    "build_analyze_graph",
    "run_analyze_v0",
]

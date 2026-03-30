"""preprocess workflow 入口。

这个文件只负责：
- 暴露测试和其他模块需要复用的公共函数
- 组装 LangGraph
- 提供 `run_preprocess_v0` 入口

节点实现、纯文本处理和 tracing 细节已经拆到独立模块，避免继续堆在一个文件里。
"""

from __future__ import annotations

from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.model_factory import MODEL_ROUTE_PREPROCESS_GUARDRAILS, validate_model_selection
from app.config.settings import get_settings
from app.llm.model_selection import ModelSelection, parse_model_selection
from app.schemas.preprocess import PreprocessAnalyzeRequest, PreprocessResult
from app.workflow.preprocess_helpers import (
    build_fallback_assessment,
    detect_language,
    detect_noise,
    detect_text_type,
    normalize_text,
    segment_text,
    split_sentences,
)
from app.workflow.preprocess_nodes import (
    PREPROCESS_SAMPLE_BUCKET,
    PREPROCESS_TRACE_SCOPE,
    build_guardrails_trace_metadata,
    detect_node,
    finalize_node,
    guardrails_node,
    normalize_node,
    segment_node,
)
from app.workflow.preprocess_state import PreprocessState
from app.workflow.tracing import build_workflow_root_metadata, build_workflow_root_tags
from app.agents.preprocess_v0 import get_guardrails_agent


PREPROCESS_SCHEMA_VERSION = "0.1.0"
PREPROCESS_WORKFLOW_VERSION = "preprocess_v0"
_build_guardrails_trace_metadata = build_guardrails_trace_metadata


def build_preprocess_graph():
    """构建 preprocess v0 的 LangGraph。"""
    graph = StateGraph(PreprocessState)
    graph.add_node("normalize", normalize_node)
    graph.add_node("segment", segment_node)
    graph.add_node("detect", detect_node)
    graph.add_node("guardrails", guardrails_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "segment")
    graph.add_edge("segment", "detect")
    graph.add_edge("detect", "guardrails")
    graph.add_edge("guardrails", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile()


async def run_preprocess_v0(
    payload: PreprocessAnalyzeRequest,
    model_selection: ModelSelection | None = None,
) -> PreprocessResult:
    """执行 preprocess v0，并为 LangSmith 建立统一的顶层 trace。"""
    graph = build_preprocess_graph()
    request_id = payload.request_id or str(uuid4())
    normalized_payload = payload if payload.request_id else payload.model_copy(update={"request_id": request_id})
    normalized_selection = parse_model_selection(model_selection or normalized_payload.model_selection)
    validate_model_selection(
        get_settings(),
        normalized_selection,
        (MODEL_ROUTE_PREPROCESS_GUARDRAILS,),
    )
    initial_state: PreprocessState = {
        "payload": normalized_payload,
        "request_id": request_id,
    }
    result = await graph.ainvoke(
        initial_state,
        config={
            "run_name": PREPROCESS_WORKFLOW_VERSION,
            "tags": build_workflow_root_tags(PREPROCESS_WORKFLOW_VERSION),
            "configurable": {
                "model_selection": normalized_selection.model_dump(exclude_none=True) if normalized_selection else None,
            },
            "metadata": build_workflow_root_metadata(
                workflow_version=PREPROCESS_WORKFLOW_VERSION,
                schema_version=PREPROCESS_SCHEMA_VERSION,
                request_id=request_id,
                profile_key=normalized_payload.profile_key,
                source_type=normalized_payload.source_type,
                trace_scope=PREPROCESS_TRACE_SCOPE,
                sample_bucket=PREPROCESS_SAMPLE_BUCKET,
                extra={
                    "model_preset": normalized_selection.preset if normalized_selection else None,
                    "runtime_model_selection": bool(normalized_selection),
                },
            ),
        },
    )
    return result["result"]


__all__ = [
    "PreprocessState",
    "PREPROCESS_SAMPLE_BUCKET",
    "PREPROCESS_SCHEMA_VERSION",
    "PREPROCESS_TRACE_SCOPE",
    "PREPROCESS_WORKFLOW_VERSION",
    "_build_guardrails_trace_metadata",
    "build_fallback_assessment",
    "build_guardrails_trace_metadata",
    "build_preprocess_graph",
    "detect_language",
    "detect_noise",
    "detect_text_type",
    "get_guardrails_agent",
    "normalize_text",
    "run_preprocess_v0",
    "segment_text",
    "split_sentences",
]

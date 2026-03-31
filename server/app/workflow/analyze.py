"""article_analysis workflow 入口。"""

from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.config.settings import get_settings
from app.llm.router import resolve_model_config, validate_model_selection
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.runtime import dump_model_selection
from app.llm.types import ModelSelection, parse_model_selection
from app.schemas.analysis import AnalysisResult, AnalyzeRequest
from app.services.analysis.user_rules import derive_user_rules
from app.workflow.analyze_nodes import (
    WORKFLOW_NAME,
    WORKFLOW_VERSION,
    assemble_result_node,
    derive_user_rules_node,
    generate_annotations_node,
    prepare_input_node,
)
from app.workflow.analyze_state import AnalyzeState
from app.workflow.tracing import build_workflow_root_metadata, build_workflow_root_tags

ANALYZE_SCHEMA_VERSION = "1.0.0"


def _collect_model_names(settings: Any, model_selection: ModelSelection | None) -> list[str]:
    model_config = resolve_model_config(
        settings,
        MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection,
    )
    if model_config and model_config.model_name:
        return [model_config.model_name]
    return []


def build_article_analysis_graph() -> Any:
    graph = StateGraph(AnalyzeState)
    graph.add_node("prepare_input", prepare_input_node)
    graph.add_node("derive_user_rules", derive_user_rules_node)
    graph.add_node("generate_annotations", generate_annotations_node)
    graph.add_node("assemble_result", assemble_result_node)

    graph.add_edge(START, "prepare_input")
    graph.add_edge("prepare_input", "derive_user_rules")
    graph.add_edge("derive_user_rules", "generate_annotations")
    graph.add_edge("generate_annotations", "assemble_result")
    graph.add_edge("assemble_result", END)
    return graph.compile()


async def run_article_analysis(payload: AnalyzeRequest) -> AnalysisResult:
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
    return cast(AnalysisResult, result["result"])


__all__ = [
    "ANALYZE_SCHEMA_VERSION",
    "WORKFLOW_NAME",
    "WORKFLOW_VERSION",
    "build_article_analysis_graph",
    "run_article_analysis",
]

from __future__ import annotations

import logging
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langsmith import get_current_run_tree, traceable
from pydantic_ai.usage import RunUsage

from app.agents.annotation import AnnotationAgentDeps
from app.config.settings import get_settings
from app.llm.router import resolve_model_config
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.runtime import get_model_selection
from app.llm.types import ModelSelection
from app.schemas.analysis import (
    AnalyzeRequestMeta,
    ArticleStructure,
    RenderSceneModel,
)
from app.schemas.internal.analysis import TeachingOutput
from app.services.analysis.input_preparation import prepare_input
from app.services.analysis.result_assembly import AssemblyOutcome, assemble_result
from app.services.analysis.runners import run_annotation_agent_raw
from app.services.analysis.user_rules import derive_user_rules
from app.workflow.analyze_state import AnalyzeState
from app.workflow.tracing import build_llm_trace_metadata, build_usage_metadata

logger = logging.getLogger(__name__)
WORKFLOW_NAME = "article_analysis"
WORKFLOW_VERSION = "v2"


def _model_selection(config: RunnableConfig | None) -> ModelSelection | None:
    return get_model_selection(config)


def _empty_result(
    *,
    request_id: str,
    payload: Any,
    profile_id: str,
    error_code: str,
    user_message: str,
) -> RenderSceneModel:
    return RenderSceneModel(
        request=AnalyzeRequestMeta(
            request_id=request_id,
            source_type=payload.source_type,
            reading_goal=payload.reading_goal,
            reading_variant=payload.reading_variant,
            profile_id=profile_id,
        ),
        article=ArticleStructure(
            source_type=payload.source_type,
            source_text=payload.text,
            render_text="",
            paragraphs=[],
            sentences=[],
        ),
        translations=[],
        inline_marks=[],
        sentence_entries=[],
        cards=[],
        warnings=[],
    )


async def prepare_input_node(state: AnalyzeState) -> AnalyzeState:
    payload = state["payload"]
    prepared_input = prepare_input(payload.text)
    warnings: list[Any] = []

    if not prepared_input.render_text.strip():
        return {
            "prepared_input": prepared_input,
            "warnings": warnings,
            "result": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id="unresolved",
                error_code="EMPTY_RENDER_TEXT",
                user_message="输入文本清洗后为空，当前无法进行英文解读。",
            ),
        }

    if prepared_input.text_type in {"code", "other"}:
        return {
            "prepared_input": prepared_input,
            "warnings": warnings,
            "result": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id="unresolved",
                error_code="UNSUPPORTED_TEXT_TYPE",
                user_message="当前输入不适合文章解读，请输入英文正文内容。",
            ),
        }

    if prepared_input.english_ratio < 0.45 or not prepared_input.sentences:
        return {
            "prepared_input": prepared_input,
            "warnings": warnings,
            "result": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id="unresolved",
                error_code="INPUT_NOT_ENGLISH_ARTICLE",
                user_message="输入文本中的英文正文不足，当前无法进行稳定标注。",
            ),
        }

    if prepared_input.noise_ratio >= 0.55:
        warnings.append(
            {
                "code": "HIGH_NOISE_RATIO",
                "message_zh": "输入中存在较多噪音内容，结果可能需要结合原文查看。",
            }
        )

    return {
        "prepared_input": prepared_input,
        "warnings": warnings,
    }


async def derive_user_rules_node(state: AnalyzeState) -> AnalyzeState:
    payload = state["payload"]
    return {"user_rules": derive_user_rules(payload.reading_goal, payload.reading_variant)}


def build_annotation_trace_metadata(
    state: AnalyzeState,
    selection: ModelSelection | None = None,
) -> dict[str, object]:
    payload = state["payload"]
    user_rules = state["user_rules"]
    model_config = resolve_model_config(
        get_settings(),
        MODEL_ROUTE_ANNOTATION_GENERATION,
        selection,
    )
    return build_llm_trace_metadata(
        workflow_name=WORKFLOW_NAME,
        workflow_version=WORKFLOW_VERSION,
        request_id=payload.request_id or "",
        source_type=payload.source_type,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
        profile_id=user_rules.profile_id,
        model_name=model_config.model_name if model_config else "unconfigured",
        model_provider=model_config.provider if model_config else "unconfigured",
        extra={
            "node": "generate_annotations",
            "model_profile": model_config.profile_name if model_config else "unconfigured",
            "sentence_count": len(state["prepared_input"].sentences),
        },
    )


async def run_annotation_llm(
    *,
    deps: AnnotationAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> TeachingOutput:
    result = await _run_annotation_llm_span(
        deps=deps,
        metadata=metadata,
        model_selection=model_selection,
    )
    current_run = get_current_run_tree()
    if current_run is not None:
        annotation_count = (
            len(result.output.inline_marks)
            + len(result.output.sentence_entries)
            + len(result.output.cards)
        )
        current_run.set(
            metadata={"annotation_count": annotation_count},
            outputs={"teaching_output": result.output.model_dump(mode="json")},
        )
    return result.output


@traceable(name="annotation_generation_llm_call", run_type="llm")
async def _run_annotation_llm_span(
    *,
    deps: AnnotationAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> Any:
    result = await run_annotation_agent_raw(deps, model_selection=model_selection)
    current_run = get_current_run_tree()
    if current_run is not None:
        annotation_count = (
            len(result.output.inline_marks)
            + len(result.output.sentence_entries)
            + len(result.output.cards)
        )
        current_run.set(
            metadata={**metadata, "annotation_count": annotation_count},
            usage_metadata=build_usage_metadata(result.usage()),
            outputs={"teaching_output": result.output.model_dump(mode="json")},
        )
    return result


async def generate_annotations_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    # V2: 检查 result 是否存在（V2 RenderSceneModel 没有 status 字段）
    if "result" in state and state["result"]:
        # 如果 result 已设置（有错误），则跳过
        return {}

    payload = state["payload"]
    prepared_input = state["prepared_input"]
    user_rules = state["user_rules"]
    model_selection = _model_selection(config)
    deps = AnnotationAgentDeps(
        user_rules=user_rules,
        sentences=[
            {
                "sentence_id": sentence.sentence_id,
                "sentence_text": sentence.text,
                "sentence_span": sentence.sentence_span.model_dump(mode="json"),
            }
            for sentence in prepared_input.sentences
        ],
        few_shot_examples=[],
    )
    try:
        output = await run_annotation_llm(
            deps=deps,
            metadata=build_annotation_trace_metadata(state, model_selection),
            model_selection=model_selection,
        )
        return {"teaching_output": output}
    except Exception as exc:
        logger.exception("generate_annotations 调用失败。")
        return {
            "result": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id=user_rules.profile_id,
                error_code="ANNOTATION_GENERATION_FAILED",
                user_message="当前解读服务繁忙，请稍后重试。",
            ),
            "warnings": [
                *state.get("warnings", []),
                {
                    "code": "ANNOTATION_GENERATION_FAILED",
                    "message_zh": f"主教学节点调用失败，原因：{type(exc).__name__}",
                },
            ],
        }


async def assemble_result_node(state: AnalyzeState) -> AnalyzeState:
    # V2: 如果 result 已存在（错误情况），直接合并警告并返回
    if "result" in state and state["result"]:
        result = state["result"]
        existing_warnings = state.get("warnings", [])
        if existing_warnings and hasattr(result, "warnings"):
            result.warnings = [*existing_warnings, *result.warnings]
        return {}

    payload = state["payload"]
    outcome = assemble_result(
        request_id=payload.request_id or "",
        source_type=payload.source_type,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
        prepared_input=state["prepared_input"],
        user_rules=state["user_rules"],
        teaching_output=state["teaching_output"],
    )
    result = outcome.result.model_copy(deep=True)
    # Merge warnings
    existing_warnings = state.get("warnings", [])
    if hasattr(result, "warnings"):
        result.warnings = [*existing_warnings, *result.warnings]
    elif existing_warnings:
        result.warnings = existing_warnings
    return {"result": result}

from __future__ import annotations

import logging
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langsmith import get_current_run_tree, traceable

from app.agents.annotation import AnnotationAgentDeps
from app.config.settings import get_settings
from app.llm.router import resolve_model_config
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.runtime import get_model_selection
from app.llm.types import ModelSelection
from app.schemas.analysis import (
    AnalysisMetrics,
    AnalysisResult,
    AnalysisStatus,
    AnalysisTranslations,
    AnalysisWarning,
    AnalyzeRequestMeta,
    ArticleStructure,
    SanitizeReport,
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
WORKFLOW_VERSION = "v1"


def _model_selection(config: RunnableConfig | None) -> ModelSelection | None:
    return get_model_selection(config)


def _empty_result(
    *,
    request_id: str,
    payload: Any,
    profile_id: str,
    status: AnalysisStatus,
    warnings: list[AnalysisWarning] | None = None,
) -> AnalysisResult:
    return AnalysisResult(
        request=AnalyzeRequestMeta(
            request_id=request_id,
            source_type=payload.source_type,
            reading_goal=payload.reading_goal,
            reading_variant=payload.reading_variant,
            profile_id=profile_id,
        ),
        status=status,
        article=ArticleStructure(
            source_type=payload.source_type,
            source_text=payload.text,
            render_text="",
            paragraphs=[],
            sentences=[],
        ),
        sanitize_report=SanitizeReport(actions=[], removed_segment_count=0),
        vocabulary_annotations=[],
        grammar_annotations=[],
        sentence_annotations=[],
        render_marks=[],
        translations=AnalysisTranslations(sentence_translations=[], full_translation_zh=""),
        warnings=warnings or [],
        metrics=AnalysisMetrics(
            vocabulary_count=0,
            grammar_count=0,
            sentence_note_count=0,
            render_mark_count=0,
            sentence_count=0,
            paragraph_count=0,
        ),
    )


async def prepare_input_node(state: AnalyzeState) -> AnalyzeState:
    payload = state["payload"]
    prepared_input = prepare_input(payload.text)
    warnings: list[AnalysisWarning] = []

    if not prepared_input.render_text.strip():
        return {
            "prepared_input": prepared_input,
            "warnings": warnings,
            "result": _empty_result(
                request_id=payload.request_id or "",
                payload=payload,
                profile_id="unresolved",
                status=AnalysisStatus(
                    state="failed",
                    is_degraded=False,
                    error_code="EMPTY_RENDER_TEXT",
                    user_message="输入文本清洗后为空，当前无法进行英文解读。",
                ),
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
                status=AnalysisStatus(
                    state="failed",
                    is_degraded=False,
                    error_code="UNSUPPORTED_TEXT_TYPE",
                    user_message="当前输入不适合文章解读，请输入英文正文内容。",
                ),
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
                status=AnalysisStatus(
                    state="failed",
                    is_degraded=False,
                    error_code="INPUT_NOT_ENGLISH_ARTICLE",
                    user_message="输入文本中的英文正文不足，当前无法进行稳定标注。",
                ),
            ),
        }

    if prepared_input.noise_ratio >= 0.55:
        warnings.append(
            AnalysisWarning(
                code="HIGH_NOISE_RATIO",
                message_zh="输入中存在较多噪音内容，结果可能需要结合原文查看。",
            )
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


@traceable(name="generate_annotations", run_type="llm")
async def run_annotation_llm(
    *,
    deps: AnnotationAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> TeachingOutput:
    result = await run_annotation_agent_raw(deps, model_selection=model_selection)
    current_run = get_current_run_tree()
    if current_run is not None:
        annotation_count = (
            len(result.output.vocabulary_annotations)
            + len(result.output.grammar_annotations)
            + len(result.output.sentence_annotations)
        )
        current_run.set(
            metadata={**metadata, "annotation_count": annotation_count},
            usage_metadata=cast(Any, build_usage_metadata(result.usage())),
            outputs={"teaching_output": result.output.model_dump(mode="json")},
        )
    return cast(TeachingOutput, result.output)


async def generate_annotations_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    if "result" in state and state["result"].status.state == "failed":
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
                status=AnalysisStatus(
                    state="failed",
                    is_degraded=False,
                    error_code="ANNOTATION_GENERATION_FAILED",
                    user_message="当前解读服务繁忙，请稍后重试。",
                ),
                warnings=[
                    *state.get("warnings", []),
                    AnalysisWarning(
                        code="ANNOTATION_GENERATION_FAILED",
                        message_zh=f"主教学节点调用失败，原因：{type(exc).__name__}",
                    ),
                ],
            )
        }


@traceable(name="assemble_result", run_type="chain")
async def assemble_result_traceable(
    *,
    request_id: str,
    source_type: str,
    reading_goal: str,
    reading_variant: str,
    prepared_input: Any,
    user_rules: Any,
    teaching_output: TeachingOutput,
) -> AssemblyOutcome:
    outcome = assemble_result(
        request_id=request_id,
        source_type=source_type,
        reading_goal=reading_goal,
        reading_variant=reading_variant,
        prepared_input=prepared_input,
        user_rules=user_rules,
        teaching_output=teaching_output,
    )
    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata={
                "workflow_name": WORKFLOW_NAME,
                "workflow_version": WORKFLOW_VERSION,
                "node": "assemble_result",
                "profile_id": user_rules.profile_id,
                "drop_count": outcome.dropped_count,
                "annotation_count": len(outcome.result.render_marks),
            },
            outputs={"result_summary": outcome.result.metrics.model_dump(mode="json")},
        )
    return outcome


async def assemble_result_node(state: AnalyzeState) -> AnalyzeState:
    if "result" in state and state["result"].status.state == "failed":
        return {}

    payload = state["payload"]
    outcome = await assemble_result_traceable(
        request_id=payload.request_id or "",
        source_type=payload.source_type,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
        prepared_input=state["prepared_input"],
        user_rules=state["user_rules"],
        teaching_output=state["teaching_output"],
    )
    result = outcome.result.model_copy(deep=True)
    result.warnings = [*state.get("warnings", []), *result.warnings]
    return {"result": result}

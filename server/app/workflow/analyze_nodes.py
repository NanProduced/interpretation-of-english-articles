from __future__ import annotations

import logging
from collections import Counter
from typing import Any, cast

from langchain_core.runnables import RunnableConfig
from langsmith import get_current_run_tree, traceable
from langsmith.schemas import ExtractedUsageMetadata

from app.agents.annotation import AnnotationAgentDeps
from app.config.settings import get_settings
from app.llm.router import resolve_model_config
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.llm.runtime import get_model_selection
from app.llm.types import ModelSelection
from app.schemas.analysis import AnalyzeRequestMeta, ArticleStructure, RenderSceneModel, Warning
from app.services.analysis.input_preparation import prepare_input
from app.services.analysis.projection import ANCHOR_FAILURE_THRESHOLD, project_to_render_scene
from app.services.analysis.runners import run_annotation_agent
from app.services.analysis.user_rules import derive_user_rules
from app.services.analysis.validators import ValidationResult, validate_annotation_output
from app.workflow.analyze_state import AnalyzeState
from app.workflow.tracing import build_llm_trace_metadata, build_usage_metadata

logger = logging.getLogger(__name__)
WORKFLOW_NAME = "article_analysis"
WORKFLOW_VERSION = "2.1.0"
MAX_ANNOTATION_ATTEMPTS = 3


# -------------------------------------------------------------------
# Module-level helpers (extracted from build_annotation_trace_metadata)
# -------------------------------------------------------------------


def _annotation_count_by_type(annotation_output: Any) -> dict[str, int]:
    counts = Counter(annotation.type for annotation in annotation_output.annotations)
    return dict(sorted(counts.items()))


def _validator_warning_items(validation_result: ValidationResult) -> list[Warning]:
    warnings: list[Warning] = []
    for error in validation_result.errors:
        warnings.append(
            Warning(
                code=f"VALIDATION_{error['code']}".upper(),
                level="error",
                message=str(error["message"]),
                sentence_id=cast(str | None, error.get("sentence_id")),
                annotation_id=cast(str | None, error.get("annotation_id")),
            )
        )
    for warning_item in validation_result.warnings:
        warnings.append(
            Warning(
                code=f"VALIDATION_{warning_item['code']}".upper(),
                level="warning",
                message=str(warning_item["message"]),
                sentence_id=cast(str | None, warning_item.get("sentence_id")),
                annotation_id=cast(str | None, warning_item.get("annotation_id")),
            )
        )
    return warnings


def _model_selection(config: RunnableConfig | None) -> ModelSelection | None:
    return get_model_selection(config)


def _empty_result(*, request_id: str, payload: Any, profile_id: str) -> RenderSceneModel:
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
            ),
        }

    if prepared_input.noise_ratio >= 0.55:
        warnings.append(
            Warning(
                code="HIGH_NOISE_RATIO",
                level="warning",
                message="输入中存在较多噪音内容，结果可能需要结合原文查看。",
            )
        )

    return {"prepared_input": prepared_input, "warnings": warnings}


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
        get_settings(), MODEL_ROUTE_ANNOTATION_GENERATION, selection
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


@traceable(name="annotation_generation_llm_call", run_type="llm")
async def _run_annotation_llm_span(
    *,
    deps: AnnotationAgentDeps,
    metadata: dict[str, object],
    model_selection: ModelSelection | None = None,
) -> dict[str, Any]:
    result = await run_annotation_agent(deps, model_selection=model_selection)
    current_run = get_current_run_tree()
    usage_meta: ExtractedUsageMetadata | None = None
    if current_run is not None:
        annotation_count = len(result.output.annotations)
        run_metadata: dict[str, object] = {
            **metadata,
            "annotation_count": annotation_count,
            "annotation_count_by_type": _annotation_count_by_type(result.output),
            "translation_count": len(result.output.sentence_translations),
        }
        run_outputs: dict[str, object] = {"annotation_output": result.output.model_dump(mode="json")}
        if hasattr(result, "usage") and callable(result.usage):
            usage = result.usage()
            if usage is not None:
                usage_meta = cast(ExtractedUsageMetadata, build_usage_metadata(usage))
        current_run.set(metadata=run_metadata, outputs=run_outputs, usage_metadata=usage_meta)
    else:
        if hasattr(result, "usage") and callable(result.usage):
            usage = result.usage()
            if usage is not None:
                usage_meta = cast(ExtractedUsageMetadata, build_usage_metadata(usage))
    return {"output": result.output, "usage": usage_meta}

@traceable(name="annotation_output_validation", run_type="chain")
async def _validate_annotation_span(
    *,
    annotation_output: Any,
    prepared_input: Any,
) -> ValidationResult:
    validation_result = validate_annotation_output(annotation_output, prepared_input)
    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata={
                "validator_error_count": len(validation_result.errors),
                "validator_warning_count": len(validation_result.warnings),
                "validator_passed": validation_result.is_valid,
            },
            outputs={
                "validator_summary": {
                    "error_count": len(validation_result.errors),
                    "warning_count": len(validation_result.warnings),
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                }
            },
        )
    return validation_result


def _anchor_failure_ratio(validation_result: ValidationResult, total_annotations: int) -> float:
    """计算锚点相关验证错误占总 annotation 数的比例。"""
    if total_annotations == 0:
        return 0.0
    anchor_error_count = sum(
        1
        for err in validation_result.errors
        if err.get("code") in ("anchor_not_substring", "chunk_not_substring")
    )
    return anchor_error_count / total_annotations


def _projection_failure_ratio(dropped_count: int, total_annotations: int) -> float:
    """计算 projection 阶段真实掉标占总 annotation 数的比例。"""
    if total_annotations == 0:
        return 0.0
    return dropped_count / total_annotations


async def generate_annotations_node(state: AnalyzeState, config: RunnableConfig) -> AnalyzeState:
    if "result" in state and state["result"]:
        return {}

    payload = state["payload"]
    prepared_input = state["prepared_input"]
    user_rules = state["user_rules"]
    model_selection = _model_selection(config)
    deps = AnnotationAgentDeps(
        user_rules=user_rules,
        sentences=[
            {"sentence_id": s.sentence_id, "text": s.text}
            for s in prepared_input.sentences
        ],
    )

    attempt = 0
    last_validation_result: ValidationResult | None = None
    last_output: Any = None
    retry_reason: str | None = None
    usage_meta: dict[str, object] | None = None

    while attempt < MAX_ANNOTATION_ATTEMPTS:
        attempt += 1
        try:
            llm_result = await _run_annotation_llm_span(
                deps=deps,
                metadata=build_annotation_trace_metadata(state, model_selection),
                model_selection=model_selection,
            )
        except Exception as exc:
            logger.exception("generate_annotations 调用失败。")
            return {
                "result": _empty_result(
                    request_id=payload.request_id or "",
                    payload=payload,
                    profile_id=user_rules.profile_id,
                ),
                "warnings": [
                    *state.get("warnings", []),
                    Warning(
                        code="ANNOTATION_GENERATION_FAILED",
                        level="error",
                        message=f"annotation LLM 调用失败（{type(exc).__name__}）：{exc}",
                    ),
                ],
            }
        if isinstance(llm_result, dict):
            output = llm_result["output"]
            usage_meta = cast(dict[str, object] | None, llm_result.get("usage"))
        else:
            output = llm_result
            usage_meta = None

        validation_result = await _validate_annotation_span(
            annotation_output=output,
            prepared_input=prepared_input,
        )

        total_annotations = len(output.annotations)
        validator_failure_ratio = _anchor_failure_ratio(validation_result, total_annotations)
        projection_outcome = project_to_render_scene(
            annotation_output=output,
            prepared_input=prepared_input,
            source_type=payload.source_type,
            reading_goal=payload.reading_goal,
            reading_variant=payload.reading_variant,
            profile_id=user_rules.profile_id,
            request_id=payload.request_id or "",
        )
        projection_failure_ratio = _projection_failure_ratio(
            projection_outcome.dropped_count,
            total_annotations,
        )
        failure_ratio = max(validator_failure_ratio, projection_failure_ratio)

        if failure_ratio <= ANCHOR_FAILURE_THRESHOLD:
            # 锚点失败率在阈值内，接受结果
            last_output = output
            last_validation_result = validation_result
            retry_reason = None
            break

        retry_reason = (
            f"validator 锚点失败率 {validator_failure_ratio:.1%}，"
            f"projection 掉标率 {projection_failure_ratio:.1%}，"
            f"超过阈值 {ANCHOR_FAILURE_THRESHOLD:.1%}"
        )
        last_output = output
        last_validation_result = validation_result
        if attempt < MAX_ANNOTATION_ATTEMPTS:
            logger.warning(
                f"generate_annotations 锚点失败率过高（第 {attempt} 次尝试）：{retry_reason}，重试。"
            )

    if last_validation_result is not None:
        validation_warnings = _validator_warning_items(last_validation_result)
    else:
        validation_warnings = []

    if retry_reason is not None and last_validation_result is not None:
        # 重试后仍超阈值，降级标记
        validation_warnings.append(
            Warning(
                code="ANCHOR_FAILURE_RATIO_EXCEEDED_AFTER_RETRY",
                level="error",
                message=f"共尝试 {MAX_ANNOTATION_ATTEMPTS} 次后锚点失败率仍超标：{retry_reason}",
            )
        )

    if last_validation_result is not None and not last_validation_result.is_valid:
        # validation 未完全通过，降级标记
        validation_warnings.append(
            Warning(
                code="ANNOTATION_VALIDATION_DEGRADED",
                level="error",
                message="annotation 验证存在错误，结果已降级。",
            )
        )

    return {
        "annotation_output": last_output,
        "annotation_usage": usage_meta if last_output is not None else None,
        "warnings": [*state.get("warnings", []), *validation_warnings],
    }


async def assemble_result_node(state: AnalyzeState) -> AnalyzeState:
    if "result" in state and state["result"]:
        result = state["result"]
        existing_warnings = state.get("warnings", [])
        if existing_warnings and hasattr(result, "warnings"):
            result.warnings = [*existing_warnings, *result.warnings]
        return {}

    payload = state["payload"]
    prepared_input = state["prepared_input"]
    user_rules = state["user_rules"]
    annotation_output = state["annotation_output"]
    outcome = project_to_render_scene(
        annotation_output=annotation_output,
        prepared_input=prepared_input,
        source_type=payload.source_type,
        reading_goal=payload.reading_goal,
        reading_variant=payload.reading_variant,
        profile_id=user_rules.profile_id,
        request_id=payload.request_id or "",
    )

    result = outcome.result.model_copy(deep=True)
    existing_warnings = state.get("warnings", [])
    projected_warnings = [Warning(**warning) for warning in outcome.warnings]
    result.warnings = [*existing_warnings, *projected_warnings]
    return {"result": result}

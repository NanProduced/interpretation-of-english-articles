import logging
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langsmith import get_current_run_tree, traceable

from app.agents.core_v0 import CoreAgentDeps, run_core_agent_raw
from app.agents.model_factory import (
    MODEL_ROUTE_ANALYSIS_CORE,
    MODEL_ROUTE_ANALYSIS_TRANSLATION,
    resolve_model_config,
)
from app.agents.translation_v0 import TranslationAgentDeps, run_translation_agent_raw
from app.config.settings import get_settings
from app.llm.model_selection import parse_model_selection
from app.schemas.analysis import (
    AnalysisAnnotations,
    AnalysisMetrics,
    AnalysisResult,
    AnalysisStatus,
    AnalysisTranslations,
    AnalysisWarning,
    AnalyzeRequestMeta,
    CoreAgentOutput,
    TranslationAgentOutput,
)
from app.schemas.preprocess import PreprocessAnalyzeRequest
from app.workflow.analyze_helpers import (
    build_article,
    build_merged_result,
    default_visible_by_priority,
    fallback_core,
    fallback_translation,
    priority_by_profile,
)
from app.workflow.analyze_state import AnalyzeState
from app.workflow.preprocess import run_preprocess_v0
from app.workflow.tracing import build_llm_trace_metadata, build_usage_metadata, infer_model_provider

logger = logging.getLogger(__name__)
ANALYZE_WORKFLOW_VERSION = "analyze_v0"
ANALYZE_TRACE_SCOPE = "analyze_local_debug"


def _config_model_selection(config: RunnableConfig | None):
    configurable = (config or {}).get("configurable", {})
    return parse_model_selection(configurable.get("model_selection"))


async def preprocess_node(state: AnalyzeState, config: RunnableConfig | None = None) -> AnalyzeState:
    payload = state["payload"]
    model_selection = _config_model_selection(config)
    preprocess = await run_preprocess_v0(
        PreprocessAnalyzeRequest(
            text=payload.text,
            profile_key=payload.profile_key,
            source_type=payload.source_type,
            request_id=payload.request_id,
            model_selection=model_selection,
        ),
        model_selection=model_selection,
    )
    warnings = [AnalysisWarning(code=item.code, message_zh=item.message_zh) for item in preprocess.warnings]
    return {"preprocess": preprocess, "warnings": warnings}


async def router_node(state: AnalyzeState) -> AnalyzeState:
    preprocess = state["preprocess"]
    if preprocess.routing.decision == "reject":
        return {
            "route_decision": "reject",
            "status": AnalysisStatus(
                state="failed",
                degraded=True,
                error_code="PREPROCESS_REJECTED",
                user_message="输入文本未通过预处理校验，暂不进入完整标注流程。",
            ),
        }

    degraded = preprocess.routing.decision == "degraded"
    return {
        "route_decision": "continue",
        "status": AnalysisStatus(
            state="success",
            degraded=degraded,
            error_code=None,
            user_message="已完成完整解读。",
        ),
    }


def build_core_trace_metadata(
    state: AnalyzeState,
    selection=None,
    *,
    chunk_index: int | None = None,
    chunk_count: int | None = None,
) -> dict[str, object]:
    settings = get_settings()
    model_config = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_CORE, selection)
    return build_llm_trace_metadata(
        workflow_version=ANALYZE_WORKFLOW_VERSION,
        request_id=state["payload"].request_id or state["preprocess"].request.request_id,
        profile_key=state["payload"].profile_key,
        source_type=state["payload"].source_type,
        trace_scope=ANALYZE_TRACE_SCOPE,
        model_name=model_config.model_name if model_config else "unconfigured",
        model_provider=infer_model_provider(model_config.base_url if model_config else "http://localhost"),
        extra={
            "node": "core_agent_v0",
            "model_profile": model_config.profile_name if model_config else "unconfigured",
            "chunk_index": chunk_index,
            "chunk_count": chunk_count,
        },
    )


def build_translation_trace_metadata(state: AnalyzeState, selection=None) -> dict[str, object]:
    settings = get_settings()
    model_config = resolve_model_config(settings, MODEL_ROUTE_ANALYSIS_TRANSLATION, selection)
    return build_llm_trace_metadata(
        workflow_version=ANALYZE_WORKFLOW_VERSION,
        request_id=state["payload"].request_id or state["preprocess"].request.request_id,
        profile_key=state["payload"].profile_key,
        source_type=state["payload"].source_type,
        trace_scope=ANALYZE_TRACE_SCOPE,
        model_name=model_config.model_name if model_config else "unconfigured",
        model_provider=infer_model_provider(model_config.base_url if model_config else "http://localhost"),
        extra={
            "node": "translation_agent_v0",
            "model_profile": model_config.profile_name if model_config else "unconfigured",
        },
    )


@traceable(name="core_llm_call", run_type="llm")
async def run_core_llm(*, deps: CoreAgentDeps, metadata: dict[str, object], model_selection=None) -> CoreAgentOutput:
    result = await run_core_agent_raw(deps, model_selection=model_selection)
    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata=metadata,
            usage_metadata=build_usage_metadata(result.usage()),
            outputs={"core_output": result.output.model_dump(mode="json")},
        )
    return result.output


@traceable(name="translation_llm_call", run_type="llm")
async def run_translation_llm(
    *,
    deps: TranslationAgentDeps,
    metadata: dict[str, object],
    model_selection=None,
) -> TranslationAgentOutput:
    result = await run_translation_agent_raw(deps, model_selection=model_selection)
    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata=metadata,
            usage_metadata=build_usage_metadata(result.usage()),
            outputs={"translation_output": result.output.model_dump(mode="json")},
        )
    return result.output


async def core_node(state: AnalyzeState, config: RunnableConfig | None = None) -> AnalyzeState:
    preprocess = state["preprocess"]
    payload = state["payload"]
    model_selection = _config_model_selection(config)
    deps = CoreAgentDeps(
        profile_key=payload.profile_key,
        sentences=[sentence.model_dump() for sentence in preprocess.segmentation.sentences],
    )
    try:
        return {
            "core_output": await run_core_llm(
                deps=deps,
                metadata=build_core_trace_metadata(state, model_selection),
                model_selection=model_selection,
            )
        }
    except Exception as exc:
        logger.exception("core_agent_v0 调用失败，当前回退到 fallback 结果。")
        warnings = list(state.get("warnings", []))
        warnings.append(
            AnalysisWarning(
                code="CORE_AGENT_FALLBACK",
                message_zh=f"核心标注 agent 调用失败，当前已回退到本地规则结果。原因：{type(exc).__name__}",
            )
        )
        status = state["status"].model_copy(
            update={
                "state": "partial_success",
                "degraded": True,
                "user_message": "核心标注部分使用了 fallback 结果。",
            }
        )
        return {
            "core_output": fallback_core(preprocess, payload.profile_key),
            "warnings": warnings,
            "status": status,
        }


async def translation_node(state: AnalyzeState, config: RunnableConfig | None = None) -> AnalyzeState:
    preprocess = state["preprocess"]
    payload = state["payload"]
    model_selection = _config_model_selection(config)
    deps = TranslationAgentDeps(
        profile_key=payload.profile_key,
        render_text=preprocess.normalized.clean_text,
        sentences=[sentence.model_dump() for sentence in preprocess.segmentation.sentences],
    )
    try:
        return {
            "translation_output": await run_translation_llm(
                deps=deps,
                metadata=build_translation_trace_metadata(state, model_selection),
                model_selection=model_selection,
            )
        }
    except Exception as exc:
        logger.exception("translation_agent_v0 调用失败，当前回退到 fallback 结果。")
        warnings = list(state.get("warnings", []))
        warnings.append(
            AnalysisWarning(
                code="TRANSLATION_AGENT_FALLBACK",
                message_zh=f"翻译 agent 调用失败，当前已回退到本地规则结果。原因：{type(exc).__name__}",
            )
        )
        status = state["status"].model_copy(
            update={
                "state": "partial_success",
                "degraded": True,
                "user_message": "翻译部分使用了 fallback 结果。",
            }
        )
        return {
            "translation_output": fallback_translation(preprocess),
            "warnings": warnings,
            "status": status,
        }


async def merge_node(state: AnalyzeState) -> AnalyzeState:
    result = build_merged_result(
        preprocess=state["preprocess"],
        payload=state["payload"],
        status=state["status"],
        warnings=state.get("warnings", []),
        core_output=state["core_output"],
        translation_output=state["translation_output"],
    )
    return {"merged_result": result}


async def enrich_node(state: AnalyzeState) -> AnalyzeState:
    result = state["merged_result"].model_copy(deep=True)
    profile_key = result.request.profile_key

    for item in result.annotations.vocabulary:
        item.priority = priority_by_profile(profile_key, item.objective_level)
        item.default_visible = default_visible_by_priority(item.priority)

    for item in result.annotations.grammar:
        item.priority = priority_by_profile(profile_key, item.objective_level)
        item.default_visible = default_visible_by_priority(item.priority)

    for item in result.annotations.difficult_sentences:
        item.priority = priority_by_profile(profile_key, item.objective_level)
        item.default_visible = default_visible_by_priority(item.priority)

    return {"merged_result": result}


async def validate_node(state: AnalyzeState) -> AnalyzeState:
    result = state["merged_result"].model_copy(deep=True)
    warnings = list(result.warnings)

    sentence_ids = {sentence.sentence_id for sentence in result.article.sentences}
    translation_ids = {item.sentence_id for item in result.translations.sentence_translations}

    if translation_ids != sentence_ids:
        warnings.append(
            AnalysisWarning(
                code="TRANSLATION_COVERAGE_MISMATCH",
                message_zh="逐句翻译未完整覆盖全部句子，当前结果存在缺口。",
            )
        )
        result.status = result.status.model_copy(
            update={
                "state": "partial_success",
                "degraded": True,
                "user_message": "部分输出未通过完整校验，请结合原文查看。",
            }
        )

    for collection_name in ("vocabulary", "grammar", "difficult_sentences"):
        items = getattr(result.annotations, collection_name)
        for item in items:
            if getattr(item, "sentence_id", None) not in sentence_ids:
                warnings.append(
                    AnalysisWarning(
                        code="INVALID_SENTENCE_REFERENCE",
                        message_zh=f"{collection_name} 中存在无法映射到正文句子的标注，已保留原始结果供排查。",
                    )
                )
                result.status = result.status.model_copy(
                    update={
                        "state": "partial_success",
                        "degraded": True,
                        "user_message": "部分标注未通过引用校验，请结合原文查看。",
                    }
                )
                break

    result.warnings = warnings
    return {"result": AnalysisResult.model_validate(result.model_dump())}


async def finalize_success_node(state: AnalyzeState) -> AnalyzeState:
    return {"result": state["result"]}


async def finalize_rejected_node(state: AnalyzeState) -> AnalyzeState:
    preprocess = state["preprocess"]
    article = build_article(preprocess, [])
    result = AnalysisResult(
        request=AnalyzeRequestMeta(
            request_id=preprocess.request.request_id,
            profile_key=preprocess.request.profile_key,
            source_type=preprocess.request.source_type,
            discourse_enabled=state["payload"].discourse_enabled,
        ),
        status=state["status"],
        article=article,
        annotations=AnalysisAnnotations(),
        translations=AnalysisTranslations(
            sentence_translations=[],
            full_translation_zh="",
            key_phrase_translations=[],
        ),
        warnings=state.get("warnings", []),
        metrics=AnalysisMetrics(
            vocabulary_count=0,
            grammar_count=0,
            difficult_sentence_count=0,
            sentence_count=len(article.sentences),
            paragraph_count=len(article.paragraphs),
        ),
    )
    return {"result": result}


def route_after_router(state: AnalyzeState) -> Literal["core", "rejected"]:
    return "rejected" if state["route_decision"] == "reject" else "core"

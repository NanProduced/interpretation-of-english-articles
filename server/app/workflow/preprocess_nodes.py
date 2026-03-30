from langchain_core.runnables import RunnableConfig
from langsmith import get_current_run_tree, traceable

from app.agents.preprocess_v0 import GuardrailsDeps
from app.config.settings import get_settings
from app.llm.router import resolve_model_config
from app.llm.routes import MODEL_ROUTE_PREPROCESS_GUARDRAILS
from app.llm.runtime import get_model_selection
from app.schemas.preprocess import (
    DetectionResult,
    PreprocessRequestMeta,
    PreprocessResult,
    PreprocessWarning,
)
from app.services.preprocess.detection import detect_language, detect_noise, detect_text_type
from app.services.preprocess.fallbacks import build_fallback_assessment
from app.services.preprocess.issues import hydrate_issues
from app.services.preprocess.normalize import normalize_text
from app.services.preprocess.runners import run_guardrails_agent
from app.services.preprocess.segmentation import segment_text
from app.workflow.preprocess_state import PreprocessState
from app.workflow.tracing import build_llm_trace_metadata, build_usage_metadata

PREPROCESS_TRACE_SCOPE = "preprocess_local_debug"
PREPROCESS_SAMPLE_BUCKET = "ad_hoc_local"


def _config_model_selection(config: RunnableConfig | None):
    return get_model_selection(config)


def build_guardrails_trace_metadata(
    state: PreprocessState,
    detection: DetectionResult,
    selection=None,
) -> dict[str, object]:
    settings = get_settings()
    model_config = resolve_model_config(settings, MODEL_ROUTE_PREPROCESS_GUARDRAILS, selection)
    return build_llm_trace_metadata(
        workflow_version="preprocess_v0",
        request_id=state["request_id"],
        profile_key=state["payload"].profile_key,
        source_type=state["payload"].source_type,
        trace_scope=PREPROCESS_TRACE_SCOPE,
        model_name=model_config.model_name if model_config else "unconfigured",
        model_provider=model_config.provider if model_config else "unconfigured",
        extra={
            "sample_bucket": PREPROCESS_SAMPLE_BUCKET,
            "node": "preprocess_guardrails",
            "model_profile": model_config.profile_name if model_config else "unconfigured",
            "text_type_predicted": detection.text_type.predicted_type,
        },
    )


@traceable(name="guardrails_llm_call", run_type="llm")
async def run_guardrails_llm(
    *,
    clean_text: str,
    deps: GuardrailsDeps,
    metadata: dict[str, object],
    model_selection=None,
):
    result = await run_guardrails_agent(clean_text, deps, model_selection=model_selection)
    current_run = get_current_run_tree()
    if current_run is not None:
        current_run.set(
            metadata=metadata,
            usage_metadata=build_usage_metadata(result.usage()),
            outputs={"assessment": result.output.model_dump(mode="json")},
        )
    return result.output


async def normalize_node(state: PreprocessState) -> PreprocessState:
    return {"normalized": normalize_text(state["payload"].text)}


async def segment_node(state: PreprocessState) -> PreprocessState:
    return {"segmentation": segment_text(state["normalized"].clean_text)}


async def detect_node(state: PreprocessState) -> PreprocessState:
    clean_text = state["normalized"].clean_text
    language = detect_language(clean_text)
    noise = detect_noise(clean_text)
    text_type = detect_text_type(clean_text, noise, state["segmentation"].sentence_count)
    return {"detection": DetectionResult(language=language, text_type=text_type, noise=noise)}


async def guardrails_node(state: PreprocessState, config: RunnableConfig | None = None) -> PreprocessState:
    detection = state["detection"]
    segmentation = state["segmentation"]
    payload = state["payload"]
    model_selection = _config_model_selection(config)
    if resolve_model_config(get_settings(), MODEL_ROUTE_PREPROCESS_GUARDRAILS, model_selection) is None:
        return {"assessment": build_fallback_assessment(detection)}

    deps = GuardrailsDeps(
        profile_key=payload.profile_key,
        paragraph_count=segmentation.paragraph_count,
        sentence_count=segmentation.sentence_count,
        english_ratio=detection.language.english_ratio,
        non_english_ratio=detection.language.non_english_ratio,
        noise_ratio=detection.noise.noise_ratio,
        has_html=detection.noise.has_html,
        has_code_like_content=detection.noise.has_code_like_content,
        appears_truncated=detection.noise.appears_truncated,
    )

    try:
        assessment = await run_guardrails_llm(
            clean_text=state["normalized"].clean_text,
            deps=deps,
            metadata=build_guardrails_trace_metadata(state, detection, model_selection),
            model_selection=model_selection,
        )
        return {"assessment": assessment}
    except Exception:
        assessment = build_fallback_assessment(detection)
        assessment.warnings.append(
            PreprocessWarning(
                code="GUARDRAILS_LLM_ERROR",
                message_zh="guardrails 模型调用失败，当前已自动回退到本地规则结果。",
            )
        )
        return {"assessment": assessment}


async def finalize_node(state: PreprocessState) -> PreprocessState:
    assessment = state["assessment"]
    request_meta = PreprocessRequestMeta(
        request_id=state["request_id"],
        profile_key=state["payload"].profile_key,
        source_type=state["payload"].source_type,
    )
    result = PreprocessResult(
        request=request_meta,
        normalized=state["normalized"],
        segmentation=state["segmentation"],
        detection=state["detection"],
        issues=hydrate_issues(state["normalized"].clean_text, assessment.issues),
        quality=assessment.quality,
        routing=assessment.routing,
        warnings=assessment.warnings,
    )
    return {"result": result}

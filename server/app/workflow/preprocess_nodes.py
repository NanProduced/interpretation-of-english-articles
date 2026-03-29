from __future__ import annotations

from langsmith import get_current_run_tree, traceable

from app.agents.preprocess_v0 import GuardrailsDeps, get_guardrails_agent
from app.config.settings import get_settings
from app.schemas.preprocess import (
    DetectionResult,
    PreprocessRequestMeta,
    PreprocessResult,
    PreprocessWarning,
)
from app.workflow.preprocess_helpers import (
    build_fallback_assessment,
    detect_language,
    detect_noise,
    detect_text_type,
    hydrate_issues,
    normalize_text,
    segment_text,
)
from app.workflow.preprocess_state import PreprocessState
from app.workflow.tracing import build_llm_trace_metadata, build_usage_metadata, infer_model_provider


PREPROCESS_TRACE_SCOPE = "preprocess_local_debug"
PREPROCESS_SAMPLE_BUCKET = "ad_hoc_local"


def build_guardrails_trace_metadata(state: PreprocessState, detection: DetectionResult) -> dict[str, object]:
    """构建 guardrails llm 子 span 的最小 metadata。"""
    settings = get_settings()
    return build_llm_trace_metadata(
        workflow_version="preprocess_v0",
        request_id=state["request_id"],
        profile_key=state["payload"].profile_key,
        source_type=state["payload"].source_type,
        trace_scope=PREPROCESS_TRACE_SCOPE,
        model_name=settings.guardrails_model_name or "unconfigured",
        model_provider=infer_model_provider(settings.guardrails_base_url),
        extra={
            "sample_bucket": PREPROCESS_SAMPLE_BUCKET,
            "node": "preprocess_guardrails",
            "text_type_predicted": detection.text_type.predicted_type,
        },
    )


@traceable(name="guardrails_llm_call", run_type="llm")
async def run_guardrails_llm(
    *,
    clean_text: str,
    deps: GuardrailsDeps,
    metadata: dict[str, object],
):
    """在 LangGraph trace 下创建 llm 子 span。"""
    agent = get_guardrails_agent()
    if agent is None:
        raise RuntimeError("Guardrails agent is not configured.")

    result = await agent.run(clean_text, deps=deps)
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


async def guardrails_node(state: PreprocessState) -> PreprocessState:
    detection = state["detection"]
    segmentation = state["segmentation"]
    payload = state["payload"]
    agent = get_guardrails_agent()

    if agent is None:
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
            metadata=build_guardrails_trace_metadata(state, detection),
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

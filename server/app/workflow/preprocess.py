from __future__ import annotations

import re
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.preprocess_v0 import GuardrailsDeps, get_guardrails_agent
from app.schemas.preprocess import (
    DetectionResult,
    GuardrailsAssessment,
    GuardrailsIssue,
    IssueSeverity,
    LanguageDetection,
    NoiseDetection,
    NormalizedText,
    PreprocessAnalyzeRequest,
    PreprocessIssue,
    PreprocessRequestMeta,
    PreprocessResult,
    PreprocessWarning,
    QualityAssessment,
    QualityGrade,
    RoutingDecision,
    RoutingDecisionType,
    SegmentedParagraph,
    SegmentedSentence,
    SegmentationResult,
    TextSpan,
    TextTypeDetection,
)


SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")
HTML_PATTERN = re.compile(r"<[^>]+>")
CODE_LIKE_PATTERN = re.compile(
    r"(```|`[^`]+`|def\s+\w+\(|class\s+\w+[:(]|function\s+\w+\(|=>|#include|SELECT\s+.+FROM)",
    re.IGNORECASE,
)
MULTISPACE_PATTERN = re.compile(r"[ \t]+")


class PreprocessState(TypedDict, total=False):
    # LangGraph 在节点之间传递的共享状态。
    payload: PreprocessAnalyzeRequest
    request_id: str
    normalized: NormalizedText
    segmentation: SegmentationResult
    detection: DetectionResult
    assessment: GuardrailsAssessment
    result: PreprocessResult


def normalize_text(source_text: str) -> NormalizedText:
    # 先把输入整理成稳定文本，后续所有 span 和切分都以 clean_text 为基准。
    actions: list[str] = []
    text = source_text.replace("\r\n", "\n").replace("\r", "\n")
    if text != source_text:
        actions.append("normalize_line_breaks")

    stripped_lines = [MULTISPACE_PATTERN.sub(" ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(line for line in stripped_lines).strip()
    if cleaned != text.strip():
        actions.append("collapse_spaces")

    return NormalizedText(
        source_text=source_text,
        clean_text=cleaned,
        text_changed=cleaned != source_text,
        normalization_actions=actions,
    )


def split_sentences(paragraph_text: str) -> list[str]:
    if not paragraph_text.strip():
        return []

    parts = SENTENCE_SPLIT_PATTERN.split(paragraph_text.strip())
    return [part.strip() for part in parts if part.strip()]


def segment_text(clean_text: str) -> SegmentationResult:
    # 这里先用规则切分，后面如果发现边界不稳，再替换成更强的切句策略。
    paragraphs: list[SegmentedParagraph] = []
    sentences: list[SegmentedSentence] = []
    offset = 0

    for paragraph_index, raw_paragraph in enumerate(clean_text.split("\n\n"), start=1):
        paragraph_text = raw_paragraph.strip()
        if not paragraph_text:
            continue

        start = clean_text.find(paragraph_text, offset)
        end = start + len(paragraph_text)
        offset = end
        paragraph_id = f"p{paragraph_index}"

        sentence_texts = split_sentences(paragraph_text)
        sentence_offset = start
        for sentence_text in sentence_texts:
            sentence_start = clean_text.find(sentence_text, sentence_offset)
            sentence_end = sentence_start + len(sentence_text)
            sentence_id = f"s{len(sentences) + 1}"
            sentence_offset = sentence_end
            sentences.append(
                SegmentedSentence(
                    sentence_id=sentence_id,
                    paragraph_id=paragraph_id,
                    text=sentence_text,
                    start=sentence_start,
                    end=sentence_end,
                )
            )

        paragraphs.append(
            SegmentedParagraph(
                paragraph_id=paragraph_id,
                text=paragraph_text,
                start=start,
                end=end,
            )
        )

    return SegmentationResult(
        paragraph_count=len(paragraphs),
        sentence_count=len(sentences),
        paragraphs=paragraphs,
        sentences=sentences,
    )


def detect_language(clean_text: str) -> LanguageDetection:
    # 当前是轻量比例检测，不做复杂语言识别，目标只是服务 guardrails 分流。
    alphabetic_chars = [char for char in clean_text if char.isalpha()]
    english_chars = [char for char in alphabetic_chars if "a" <= char.lower() <= "z"]
    total = len(alphabetic_chars)
    english_ratio = len(english_chars) / total if total else 0.0

    return LanguageDetection(
        primary_language="en" if english_ratio >= 0.5 else "mixed",
        english_ratio=round(english_ratio, 4),
        non_english_ratio=round(max(0.0, 1.0 - english_ratio), 4),
    )


def detect_noise(clean_text: str) -> NoiseDetection:
    html_matches = HTML_PATTERN.findall(clean_text)
    code_like = bool(CODE_LIKE_PATTERN.search(clean_text))
    appears_truncated = clean_text.endswith(("...", "…")) or clean_text.count("(") > clean_text.count(")")

    noise_units = sum(len(match) for match in html_matches)
    if code_like:
        noise_units += max(10, len(clean_text) // 8)

    noise_ratio = min(1.0, noise_units / max(1, len(clean_text)))
    return NoiseDetection(
        noise_ratio=round(noise_ratio, 4),
        has_html=bool(html_matches),
        has_code_like_content=code_like,
        appears_truncated=appears_truncated,
    )


def detect_text_type(clean_text: str, noise: NoiseDetection, sentence_count: int) -> TextTypeDetection:
    if noise.has_code_like_content:
        predicted_type = "code"
        confidence = 0.85
    elif "@" in clean_text and clean_text.lower().count("subject:"):
        predicted_type = "email"
        confidence = 0.7
    elif clean_text.count("\n") > 2 and clean_text.count("- ") + clean_text.count("* ") >= 2:
        predicted_type = "list"
        confidence = 0.7
    elif len(clean_text) < 60 and sentence_count <= 1:
        predicted_type = "subtitle"
        confidence = 0.6
    else:
        predicted_type = "article"
        confidence = 0.8

    return TextTypeDetection(predicted_type=predicted_type, confidence=confidence)


def build_fallback_assessment(detection: DetectionResult) -> GuardrailsAssessment:
    # 当模型不可用时，至少给出可联调的确定性结果，避免整个链路直接中断。
    issues: list[GuardrailsIssue] = []
    warnings: list[PreprocessWarning] = []

    if detection.language.english_ratio < 0.5:
        issues.append(
            GuardrailsIssue(
                type="non_english_content",
                severity=IssueSeverity.HIGH,
                description_zh="文本中的非英文内容占比较高，可能不适合完整英文解读。",
                suggestion_zh="请尽量输入英文正文，或减少混杂的中文与其他语言内容。",
            )
        )

    if detection.noise.noise_ratio >= 0.2 or detection.noise.has_html or detection.noise.has_code_like_content:
        issues.append(
            GuardrailsIssue(
                type="noise_content",
                severity=IssueSeverity.MEDIUM,
                description_zh="文本中包含较多噪音内容，可能影响句子切分与后续标注。",
                suggestion_zh="建议去除 HTML、代码片段或无关噪音后再分析。",
            )
        )

    if detection.noise.appears_truncated:
        issues.append(
            GuardrailsIssue(
                type="truncated_text",
                severity=IssueSeverity.MEDIUM,
                description_zh="文本可能被截断，部分句子不完整。",
                suggestion_zh="建议补全原文后再进行解读。",
            )
        )

    if detection.text_type.predicted_type in {"code", "other"}:
        issues.append(
            GuardrailsIssue(
                type="unsupported_text_type",
                severity=IssueSeverity.HIGH,
                description_zh="当前文本类型不适合文章解读流程。",
                suggestion_zh="请输入英文文章、段落或阅读材料。",
            )
        )

    decision = RoutingDecisionType.FULL
    score = 0.85
    summary = "文本质量较好，可进入完整解读流程。"
    degrade_reason = None
    reject_reason = None

    if any(issue.type == "unsupported_text_type" and issue.severity == IssueSeverity.HIGH for issue in issues):
        decision = RoutingDecisionType.REJECT
        score = 0.2
        summary = "文本类型不适合当前解读流程。"
        reject_reason = "unsupported_text_type"
    elif detection.language.english_ratio < 0.5:
        decision = RoutingDecisionType.REJECT
        score = 0.25
        summary = "文本中的非英文内容过多，不适合完整英文解读。"
        reject_reason = "non_english_content"
    elif issues:
        decision = RoutingDecisionType.DEGRADED
        score = 0.6
        summary = "文本可继续处理，但建议以降级模式运行后续流程。"
        degrade_reason = "input_quality_risk"

    warnings.append(
        PreprocessWarning(
            code="GUARDRAILS_FALLBACK",
            message_zh="未配置 guardrails 模型，当前结果由本地规则生成，可用于联调但不代表最终效果。",
        )
    )

    grade = QualityGrade.GOOD
    if score < 0.4:
        grade = QualityGrade.POOR
    elif score < 0.75:
        grade = QualityGrade.ACCEPTABLE

    return GuardrailsAssessment(
        text_type=detection.text_type.predicted_type,
        issues=issues,
        quality=QualityAssessment(
            score=score,
            grade=grade,
            suitable_for_full_annotation=decision == RoutingDecisionType.FULL,
            summary_zh=summary,
        ),
        routing=RoutingDecision(
            decision=decision,
            should_continue=decision != RoutingDecisionType.REJECT,
            degrade_reason=degrade_reason,
            reject_reason=reject_reason,
        ),
        warnings=warnings,
    )


def _build_issue_span(clean_text: str, issue: GuardrailsIssue) -> TextSpan | None:
    if issue.type == "truncated_text":
        start = max(0, len(clean_text) - 20)
        return TextSpan(start=start, end=max(start + 1, len(clean_text)))
    return None


def _hydrate_issues(clean_text: str, issues: list[GuardrailsIssue]) -> list[PreprocessIssue]:
    hydrated: list[PreprocessIssue] = []
    for index, issue in enumerate(issues, start=1):
        hydrated.append(
            PreprocessIssue(
                issue_id=f"pi{index}",
                type=issue.type,
                severity=issue.severity,
                span=_build_issue_span(clean_text, issue),
                description_zh=issue.description_zh,
                suggestion_zh=issue.suggestion_zh,
            )
        )
    return hydrated


async def normalize_node(state: PreprocessState) -> PreprocessState:
    normalized = normalize_text(state["payload"].text)
    return {"normalized": normalized}


async def segment_node(state: PreprocessState) -> PreprocessState:
    segmentation = segment_text(state["normalized"].clean_text)
    return {"segmentation": segmentation}


async def detect_node(state: PreprocessState) -> PreprocessState:
    clean_text = state["normalized"].clean_text
    language = detect_language(clean_text)
    noise = detect_noise(clean_text)
    text_type = detect_text_type(clean_text, noise, state["segmentation"].sentence_count)
    return {
        "detection": DetectionResult(
            language=language,
            text_type=text_type,
            noise=noise,
        )
    }


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
        # metadata 会进入 LangSmith，后面排查样本和 trace 时会直接用到。
        result = await agent.run(
            state["normalized"].clean_text,
            deps=deps,
            metadata={
                "node": "preprocess_guardrails",
                "workflow_version": "preprocess_v0",
                "schema_version": "0.1.0",
                "profile_key": payload.profile_key,
                "source_type": payload.source_type,
            },
        )
        return {"assessment": result.output}
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
    # 最后统一收口成外部接口返回的结构，避免路由层再做拼装。
    assessment = state["assessment"]
    normalized = state["normalized"]
    request_meta = PreprocessRequestMeta(
        request_id=state["request_id"],
        profile_key=state["payload"].profile_key,
        source_type=state["payload"].source_type,
    )
    result = PreprocessResult(
        request=request_meta,
        normalized=normalized,
        segmentation=state["segmentation"],
        detection=state["detection"],
        issues=_hydrate_issues(normalized.clean_text, assessment.issues),
        quality=assessment.quality,
        routing=assessment.routing,
        warnings=assessment.warnings,
    )
    return {"result": result}


def build_preprocess_graph():
    # 当前 preprocess 是线性图，后续引入条件分流时再从这里扩展。
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


async def run_preprocess_v0(payload: PreprocessAnalyzeRequest) -> PreprocessResult:
    # 每次请求都从一个干净的初始状态启动，便于后续对单次 trace 做回放和定位。
    graph = build_preprocess_graph()
    initial_state: PreprocessState = {
        "payload": payload,
        "request_id": payload.request_id or str(uuid4()),
    }
    result = await graph.ainvoke(initial_state)
    return result["result"]

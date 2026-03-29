from __future__ import annotations

import re

from app.schemas.preprocess import (
    DetectionResult,
    GuardrailsAssessment,
    GuardrailsIssue,
    IssueSeverity,
    LanguageDetection,
    NoiseDetection,
    NormalizedText,
    PreprocessIssue,
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


def normalize_text(source_text: str) -> NormalizedText:
    """规范化输入文本，供后续切分和定位统一使用。"""
    actions: list[str] = []
    text = source_text.replace("\r\n", "\n").replace("\r", "\n")
    if text != source_text:
        actions.append("normalize_line_breaks")

    stripped_lines = [MULTISPACE_PATTERN.sub(" ", line).strip() for line in text.split("\n")]
    cleaned = "\n".join(stripped_lines).strip()
    if cleaned != text.strip():
        actions.append("collapse_spaces")

    return NormalizedText(
        source_text=source_text,
        clean_text=cleaned,
        text_changed=cleaned != source_text,
        normalization_actions=actions,
    )


def split_sentences(paragraph_text: str) -> list[str]:
    """按基础标点规则把段落切成句子。"""
    if not paragraph_text.strip():
        return []
    return [part.strip() for part in SENTENCE_SPLIT_PATTERN.split(paragraph_text.strip()) if part.strip()]


def segment_text(clean_text: str) -> SegmentationResult:
    """把清洗后的文本切成段落和句子，并保留绝对位置。"""
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

        sentence_offset = start
        for sentence_text in split_sentences(paragraph_text):
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
    """用轻量字符比例判断文本的英文占比。"""
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
    """检测 HTML、代码样式内容和疑似截断文本。"""
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
    """粗略识别文本类型，供 guardrails 做分流。"""
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
    """在 guardrails 模型不可用时，用本地规则生成可用结果。"""
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
    """为可定位的问题补充原文位置。"""
    if issue.type == "truncated_text":
        start = max(0, len(clean_text) - 20)
        return TextSpan(start=start, end=max(start + 1, len(clean_text)))
    return None


def hydrate_issues(clean_text: str, issues: list[GuardrailsIssue]) -> list[PreprocessIssue]:
    """把 guardrails 的内部 issue 转成对外输出格式。"""
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

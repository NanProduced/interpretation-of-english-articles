from __future__ import annotations

from app.schemas.preprocess import (
    DetectionResult,
    GuardrailsAssessment,
    GuardrailsIssue,
    IssueSeverity,
    PreprocessWarning,
    QualityAssessment,
    QualityGrade,
    RoutingDecision,
    RoutingDecisionType,
)


def build_fallback_assessment(detection: DetectionResult) -> GuardrailsAssessment:
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


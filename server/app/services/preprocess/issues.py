from __future__ import annotations

from app.schemas.common import TextSpan
from app.schemas.preprocess import GuardrailsIssue, PreprocessIssue


def _build_issue_span(clean_text: str, issue: GuardrailsIssue) -> TextSpan | None:
    if issue.type == "truncated_text":
        start = max(0, len(clean_text) - 20)
        return TextSpan(start=start, end=max(start + 1, len(clean_text)))
    return None


def hydrate_issues(clean_text: str, issues: list[GuardrailsIssue]) -> list[PreprocessIssue]:
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

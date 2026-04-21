"""Quality review agent for Daily Reader workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.daily_drafts import DailyReviewDraft
from app.services.analysis.prompting.daily_prompt_strategy import (
    DailyPromptStrategy,
    build_daily_prompt_sections,
    build_quality_review_strategy,
)


@dataclass
class DailyReviewAgentDeps:
    original_text: str
    highlights_json: str
    footer_analysis_json: str
    full_interpretation: str
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_quality_review_strategy)


DAILY_REVIEW_INSTRUCTIONS = """
你是一位质量审核助手，审核每日精读的 AI 生成内容质量。

审核维度（6 个）：
1. highlight_accuracy：高亮锚点是否准确（text 是否在原文中存在）
2. highlight_density：高亮密度是否合理（每段 3-5 个，不超不缺）
3. footer_completeness：文末解析是否完整（6 个模块是否齐全）
4. footer_accuracy：文末解析内容是否准确（摘要、结构、关键表达是否正确）
5. interpretation_coherence：全篇讲解是否连贯、有逻辑
6. annotation_consistency：标注之间是否一致（无矛盾、无重复）

对每个维度给出 pass/fail 和具体问题描述。
如果有任何维度 fail，给出修改建议。
overall_score 为 0-10 分。
passed 为 true 当且仅当所有维度都 pass 或只有 minor 问题。
""".strip()


def build_daily_review_prompt(deps: DailyReviewAgentDeps) -> str:
    from app.services.analysis.prompting.prompt_composer import render_prompt_sections, PromptSection

    sections = build_daily_prompt_sections(deps.prompt_strategy)
    all_sections = list(sections) + [
        PromptSection("original_text", (deps.original_text[:4000],)),
        PromptSection("highlights", (deps.highlights_json[:3000],)),
        PromptSection("footer_analysis", (deps.footer_analysis_json[:3000],)),
        PromptSection("full_interpretation", (deps.full_interpretation[:3000],)),
    ]
    return render_prompt_sections(all_sections)


@lru_cache(maxsize=1)
def get_daily_review_agent() -> Agent[DailyReviewAgentDeps, DailyReviewDraft]:
    return Agent[DailyReviewAgentDeps, DailyReviewDraft](
        model=None,
        output_type=DailyReviewDraft,
        deps_type=DailyReviewAgentDeps,
        instructions=DAILY_REVIEW_INSTRUCTIONS,
        name="daily_review_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

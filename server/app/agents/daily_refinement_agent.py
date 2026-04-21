"""Refinement agent for Daily Reader workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.daily_drafts import DailyRefinementDraft
from app.services.analysis.prompting.daily_prompt_strategy import (
    DailyPromptStrategy,
    build_daily_prompt_sections,
    build_refinement_strategy,
)


@dataclass
class DailyRefinementAgentDeps:
    original_text: str
    review_issues: str
    current_highlights: str = ""
    current_footer: str = ""
    current_interpretation: str = ""
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_refinement_strategy)


DAILY_REFINEMENT_INSTRUCTIONS = """
你是一位内容修正助手，根据质量审核结果修正每日精读内容。

只修正审核指出的具体问题，不要重新生成全部内容。
如果问题无法修正（如文章本身不适合精读），设置 abort=true。
仅执行一轮修正，不进行二次审核。

对于需要修正的高亮，输出 refined_highlights（完整的修正后高亮列表）。
对于需要修正的文末解析，输出 refined_footer（完整的修正后解析）。
对于需要修正的全篇讲解，输出 refined_interpretation（修正后的讲解文本）。
不需要修正的部分，对应字段留空。
""".strip()


def build_daily_refinement_prompt(deps: DailyRefinementAgentDeps) -> str:
    from app.services.analysis.prompting.prompt_composer import render_prompt_sections, PromptSection

    sections = build_daily_prompt_sections(deps.prompt_strategy)
    all_sections = list(sections) + [
        PromptSection("original_text", (deps.original_text[:4000],)),
        PromptSection("review_issues", (deps.review_issues,)),
    ]
    if deps.current_highlights:
        all_sections.append(PromptSection("current_highlights", (deps.current_highlights[:3000],)))
    if deps.current_footer:
        all_sections.append(PromptSection("current_footer", (deps.current_footer[:3000],)))
    if deps.current_interpretation:
        all_sections.append(PromptSection("current_interpretation", (deps.current_interpretation[:3000],)))
    return render_prompt_sections(all_sections)


@lru_cache(maxsize=1)
def get_daily_refinement_agent() -> Agent[DailyRefinementAgentDeps, DailyRefinementDraft]:
    return Agent[DailyRefinementAgentDeps, DailyRefinementDraft](
        model=None,
        output_type=DailyRefinementDraft,
        deps_type=DailyRefinementAgentDeps,
        instructions=DAILY_REFINEMENT_INSTRUCTIONS,
        name="daily_refinement_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

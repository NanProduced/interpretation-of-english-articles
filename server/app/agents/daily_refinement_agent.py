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
from app.services.analysis.prompting.prompt_loader import load_agent_instructions


@dataclass
class DailyRefinementAgentDeps:
    original_text: str
    review_issues: str
    current_highlights: str = ""
    current_footer: str = ""
    current_interpretation: str = ""
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_refinement_strategy)


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
        instructions=load_agent_instructions("daily_refinement"),
        name="daily_refinement_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

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
from app.services.analysis.prompting.prompt_loader import load_agent_instructions


@dataclass
class DailyReviewAgentDeps:
    original_text: str
    highlights_json: str
    footer_analysis_json: str
    full_interpretation: str
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_quality_review_strategy)


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
        instructions=load_agent_instructions("daily_review"),
        name="daily_review_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

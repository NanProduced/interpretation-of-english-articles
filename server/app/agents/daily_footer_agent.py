"""Footer analysis agent for Daily Reader workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.daily_drafts import DailyFooterDraft
from app.services.analysis.prompting.daily_prompt_strategy import (
    DailyPromptStrategy,
    build_daily_prompt_sections,
    build_footer_analysis_strategy,
)
from app.services.analysis.prompting.prompt_loader import load_agent_instructions


@dataclass
class DailyFooterAgentDeps:
    full_text: str
    title: str
    highlights_summary: str = ""
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_footer_analysis_strategy)


def build_daily_footer_prompt(deps: DailyFooterAgentDeps) -> str:
    from app.services.analysis.prompting.prompt_composer import render_prompt_sections, PromptSection

    sections = build_daily_prompt_sections(deps.prompt_strategy)
    all_sections = list(sections) + [
        PromptSection("article_info", (
            f"Title: {deps.title}",
        )),
        PromptSection("full_text", (deps.full_text[:6000],)),
    ]
    if deps.highlights_summary:
        all_sections.append(PromptSection("highlights_context", (deps.highlights_summary,)))
    return render_prompt_sections(all_sections)


@lru_cache(maxsize=1)
def get_daily_footer_agent() -> Agent[DailyFooterAgentDeps, DailyFooterDraft]:
    return Agent[DailyFooterAgentDeps, DailyFooterDraft](
        model=None,
        output_type=DailyFooterDraft,
        deps_type=DailyFooterAgentDeps,
        instructions=load_agent_instructions("daily_footer"),
        name="daily_footer_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

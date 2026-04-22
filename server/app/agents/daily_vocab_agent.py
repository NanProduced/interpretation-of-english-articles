"""Vocabulary highlight agent for Daily Reader workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.daily_drafts import DailyVocabDraft
from app.services.analysis.prompting.daily_prompt_strategy import (
    DailyPromptStrategy,
    build_daily_prompt_sections,
    build_vocab_highlight_strategy,
)
from app.services.analysis.prompting.prompt_loader import load_agent_instructions


@dataclass
class DailyVocabAgentDeps:
    paragraphs: list[dict[str, object]]
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_vocab_highlight_strategy)


def build_daily_vocab_prompt(deps: DailyVocabAgentDeps) -> str:
    from app.services.analysis.prompting.prompt_composer import render_prompt_sections

    sections = build_daily_prompt_sections(deps.prompt_strategy)
    paragraph_lines = []
    for p in deps.paragraphs:
        pid = p.get("paragraph_id", "")
        text = p.get("text", "")
        paragraph_lines.append(f"{pid}: {text}")

    all_sections = list(sections) + [
        __import__("app.services.analysis.prompting.prompt_composer", fromlist=["PromptSection"]).PromptSection(
            "input_paragraphs", tuple(paragraph_lines)
        ),
    ]
    return render_prompt_sections(all_sections)


@lru_cache(maxsize=1)
def get_daily_vocab_agent() -> Agent[DailyVocabAgentDeps, DailyVocabDraft]:
    return Agent[DailyVocabAgentDeps, DailyVocabDraft](
        model=None,
        output_type=DailyVocabDraft,
        deps_type=DailyVocabAgentDeps,
        instructions=load_agent_instructions("daily_vocab"),
        name="daily_vocab_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

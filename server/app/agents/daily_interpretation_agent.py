"""Full interpretation agent for Daily Reader workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.daily_drafts import DailyInterpretationDraft
from app.services.analysis.prompting.daily_prompt_strategy import (
    DailyPromptStrategy,
    build_daily_prompt_sections,
    build_full_interpretation_strategy,
)


@dataclass
class DailyInterpretationAgentDeps:
    full_text: str
    title: str
    footer_summary: str = ""
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_full_interpretation_strategy)


DAILY_INTERPRETATION_INSTRUCTIONS = """
你是一位英语文章讲解助手，为每日精读生成全篇讲解。

生成一篇连贯的讲解式文章解析（不是逐句拆解），帮助读者深入理解文章。
讲解风格：像一位优秀的英语老师在课堂上讲解文章——先讲大意，再讲结构，最后讲亮点。
要涵盖：文章的核心论点、论证逻辑、写作手法、语言亮点。
用中文撰写，关键英文表达保留原文。
长度：500-1000 字。
""".strip()


def build_daily_interpretation_prompt(deps: DailyInterpretationAgentDeps) -> str:
    from app.services.analysis.prompting.prompt_composer import render_prompt_sections, PromptSection

    sections = build_daily_prompt_sections(deps.prompt_strategy)
    all_sections = list(sections) + [
        PromptSection("article_info", (f"Title: {deps.title}",)),
        PromptSection("full_text", (deps.full_text[:6000],)),
    ]
    if deps.footer_summary:
        all_sections.append(PromptSection("footer_context", (deps.footer_summary,)))
    return render_prompt_sections(all_sections)


@lru_cache(maxsize=1)
def get_daily_interpretation_agent() -> Agent[DailyInterpretationAgentDeps, DailyInterpretationDraft]:
    return Agent[DailyInterpretationAgentDeps, DailyInterpretationDraft](
        model=None,
        output_type=DailyInterpretationDraft,
        deps_type=DailyInterpretationAgentDeps,
        instructions=DAILY_INTERPRETATION_INSTRUCTIONS,
        name="daily_interpretation_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

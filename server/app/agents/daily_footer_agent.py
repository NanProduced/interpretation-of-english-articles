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


@dataclass
class DailyFooterAgentDeps:
    full_text: str
    title: str
    highlights_summary: str = ""
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_footer_analysis_strategy)


DAILY_FOOTER_INSTRUCTIONS = """
你是一位英语文章深度分析助手，为每日精读生成文末解析内容。

你需要生成以下内容：
1. summary：一句话摘要（中文）
2. thesis_and_intent：包含 thesis（文章主旨）和 author_intent（作者意图）的对象
3. structure：文章结构分解（2-4 个部分，每部分含 label、title、summary）
4. key_expressions：3-5 个关键表达（含 expression、gloss、context_sentence）
5. misreading_points：1-3 个易误读点（含 point、clarification）
6. discussion_questions：2-3 个讨论问题（英文）

分析要有深度，帮助中国英语学习者理解文章的深层含义和写作技巧。
不要逐句翻译，要提供有洞察力的分析。
""".strip()


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
        instructions=DAILY_FOOTER_INSTRUCTIONS,
        name="daily_footer_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

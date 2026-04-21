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


@dataclass
class DailyVocabAgentDeps:
    paragraphs: list[dict[str, object]]
    prompt_strategy: DailyPromptStrategy = field(default_factory=build_vocab_highlight_strategy)


DAILY_VOCAB_INSTRUCTIONS = """
你是一位英语阅读词汇标注助手，专门为每日精读功能服务。

你的任务是为每段英文标注核心词汇和短语，帮助中国英语学习者理解文章。

标注原则：克制、精准。每段不超过 3-5 个标注，优先标注 B1-C1 级词汇。

三种标注用途：
- vocab_highlight：单个词，用户可能不认识或需要记住
- phrase_gloss：多词表达（短语动词、固定搭配、术语），需要整体解释
- context_gloss：词在当前语境下的意思和常见义不同，需要专门说明

如果同一个词同时适合多种标注，只选最合适的一种。
常见词（如 the, is, have, make 等）不标。只标真正影响理解或有学习价值的词。
锚点 anchor 必须从原文中精确摘取，不要改写、不要拼写变化。
输出前必须回查：你标注的每个 anchor 字段，是否能在段落文本中逐字找到？如果找不到，删除该标注。
""".strip()


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
        instructions=DAILY_VOCAB_INSTRUCTIONS,
        name="daily_vocab_agent",
        retries=2,
        output_retries=3,
        instrument=False,
    )

"""Translation agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import TranslationDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_strategy import PromptStrategy


@dataclass
class TranslationAgentDeps:
    """Translation agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


TRANSLATION_INSTRUCTIONS = """
你是一名翻译标注器，负责英文文章的逐句翻译。

任务：为每个英文句子生成中文翻译。

【核心原则】
1. 逐句翻译完整，所有句子都必须有翻译。
2. 翻译要自然流畅，符合中文表达习惯。
3. 句间翻译保持连贯。
4. 不添加额外解释，不输出 schema 之外的内容。

【翻译风格】
1. 自然流畅的中文。
2. 保留原句的语气和重点。
3. 专有名词、术语可保留英文或括注中文。

【输出前自检】
1. 所有句子都有翻译。
2. 翻译是通顺的中文，不是逐字硬译。
""".strip()


def _render_strategy(strategy: PromptStrategy) -> list[str]:
    lines = [
        f"- reading_goal: {strategy.reading_goal}",
        f"- reading_variant: {strategy.reading_variant}",
    ]
    if strategy.translation_style:
        lines.append(f"- translation_style: {strategy.translation_style}")
    if strategy.translation_style == "natural":
        lines.append("- 执行方式: 优先自然、通顺、忠实的中文表达。")
    elif strategy.translation_style == "academic":
        lines.append("- 执行方式: 保留更正式、更书面的语气。")
    elif strategy.translation_style == "exam":
        lines.append("- 执行方式: 表达清晰直白，便于学习者理解句子结构。")
    return lines


def _render_examples(examples: list[ExampleEntry]) -> list[str]:
    if not examples:
        return []
    lines = ["补充示例："]
    for idx, example in enumerate(examples, start=1):
        lines.extend(
            [
                f"{idx}. [{example.example_type}] {example.sentence_text}",
                example.output_fragment,
            ]
        )
    return lines


def build_translation_prompt(deps: TranslationAgentDeps) -> str:
    sentence_lines = [
        f"{sentence['sentence_id']}: {sentence['text']}"
        for sentence in deps.sentences
    ]
    return "\n".join(
        [
            "策略：",
            *_render_strategy(deps.prompt_strategy),
            *(_render_examples(deps.examples)),
            "句子列表：",
            *sentence_lines,
        ]
    )


@lru_cache(maxsize=1)
def get_translation_agent() -> Agent[TranslationAgentDeps, TranslationDraft]:
    return Agent[TranslationAgentDeps, TranslationDraft](
        model=None,
        output_type=TranslationDraft,
        deps_type=TranslationAgentDeps,
        instructions=TRANSLATION_INSTRUCTIONS,
        name="translation_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

"""Translation agent for V3 workflow.

负责逐句翻译。
设计原则：
- 逐句翻译完整优先于风格花哨
- 独立完成，不依赖 annotation 链路
- 缺失应有明确 warning，不允许静默吞掉
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import TranslationDraft


@dataclass
class TranslationAgentDeps:
    """Translation agent 依赖。"""
    sentences: list[dict[str, object]]


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


def build_translation_prompt(deps: TranslationAgentDeps) -> str:
    sentence_lines = [
        f"{sentence['sentence_id']}: {sentence['text']}"
        for sentence in deps.sentences
    ]
    return "\n".join(
        [
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

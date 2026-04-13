"""Translation agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import TranslationDraft
from app.services.analysis.prompting.example_strategy import ExampleEntry
from app.services.analysis.prompting.prompt_composer import build_agent_prompt
from app.services.analysis.prompting.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class TranslationAgentDeps:
    """Translation agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


TRANSLATION_INSTRUCTIONS = """
你是英语阅读翻译标注器，为英文文章生成逐句中文翻译。

核心原则（必须严格遵守）：
1. Schema 约束输出结构，所有句子都必须有对应翻译，绝不允许遗漏或合并多句为一句。
2. 句间翻译必须保持连贯，前后文代词指代要一致。
3. 必须额外输出一个中文标题 `title`，用于历史记录展示。
4. 绝不输出 schema 之外的内容（不加备注，不写引言）。

标题生成硬性约束：
1. 标题必须概括全文主旨。
2. 必须使用中文短标题，不带结尾句号，不使用 Emoji。

翻译处理红线：
- 即使是标题、小标题、图注等非完整句，也必须以单独的 sentence_id 原样翻译。
- 引用内容照常翻译，绝不允许额外补全诸如“原文引用：”的前缀。
- 原文内容中包含的专有名词或学术术语，首次出现建议按照"中文（英文）"的格式翻译，但如已有成熟译名且不产生歧义，则以准确传达为主。
""".strip()

def build_translation_prompt(deps: TranslationAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
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

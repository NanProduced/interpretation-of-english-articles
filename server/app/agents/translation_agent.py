"""Translation agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import TranslationDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_composer import build_agent_prompt
from app.services.analysis.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class TranslationAgentDeps:
    """Translation agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


TRANSLATION_INSTRUCTIONS = """
你是英语阅读翻译标注器，为英文文章生成逐句中文翻译。

核心原则：
1. 所有句子都必须有翻译，不得遗漏。
2. 句间翻译保持连贯，前后文代词指代要一致。
3. 不输出 schema 之外的内容。

翻译风格（基线：自然意译）：
1. 用自然流畅的中文表达，允许为了中文通顺而调整语序。
2. 保留原句的语气和重点，不改变信息量。
3. 英文中省略但中文需要的成分，适当补全以保证可读性。
4. 长句翻译时保持为一句中文，不拆分为多句（除非原句本身含分号或破折号分隔的独立部分）。

专名与术语处理：
- 人名：保留英文原名，不音译（如 Andrew Smith → Andrew Smith）。
- 机构名/品牌名：首次出现时"中文（英文）"，如"烂番茄（Rotten Tomatoes）"；后续直接用中文。
- 学术术语：首次出现时"中文（英文）"，如"温室效应（greenhouse effect）"；后续直接用中文。
- 无通用中文译名的术语直接保留英文。

边界情况：
- 标题、小标题、图注等非完整句也需翻译。
- 引用内容照常翻译，不加引号标注"原文引用"。
- 括号内容随句翻译，不单独处理。

【示例 1：普通句 · 自然意译】
原句："The visuals rendered the ancient world far more vivid than earlier documentaries."
翻译：这些画面把远古世界呈现得比以往的纪录片生动得多。
→ 语序微调（把 far more vivid 提前），补全了"这些"让中文更自然。

【示例 2：含专名的句子】
原句："The documentary scored 100 per cent on Rotten Tomatoes, making it the highest-rated nature film."
翻译：这部纪录片在烂番茄（Rotten Tomatoes）上获得了百分之百的好评，成为评分最高的自然类影片。
→ 机构名首次出现用"中文（英文）"格式。
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

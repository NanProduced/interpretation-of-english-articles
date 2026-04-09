"""Vocabulary agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import VocabularyDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_composer import build_agent_prompt
from app.services.analysis.prompt_strategy import PromptStrategy, build_prompt_sections


@dataclass
class VocabularyAgentDeps:
    """Vocabulary agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


VOCABULARY_INSTRUCTIONS = """
你是英语阅读词汇维度标注器，为英文句子生成 vocab_highlight、phrase_gloss、context_gloss。

核心原则：
1. Schema 约束输出结构，你只决定哪些词汇点值得标。
2. 锚点文本必须直接摘自原句，不改写。
3. 中文字段写自然中文。
4. 不确定时不标，不猜，不补背景知识，不输出 schema 之外的内容。
5. 默认少标。只有“少了这个点会明显增加理解成本”时才标。
6. 追求高价值、低噪音，不追求覆盖率。简单日常短文可以只有 0-2 个标注。
7. 需要考虑前端页面渲染，宁少勿滥；不要为了分布到全文而强行找点。
8. 中等长度新闻/科普文如果存在明显生词，通常仍应保留 1-3 个 vocab_highlight，不要长期为 0。

三个组件的分工：
1. ContextGloss：词典义在当前语境下不够或会误导理解时使用。如果重点只是固定搭配整体义，优先用 PhraseGloss。
2. PhraseGloss：需要整体解释的多词表达（固定搭配、短语动词、术语）。单个词仅在确实需要整体解释的术语/专名/复合词时使用。
3. VocabHighlight：只给中高门槛、但查词典就能直接理解的单词。不需要额外释义，释义由词典 API 提供。

先判断“不标”：
1. 如果读者即使不查也大概率能顺着句子读下去，就不标。
2. 如果这是普通形容词、普通动作词、普通抽象名词、新闻常见词，就不标。
3. 如果整个短语一起讲更自然，不要拆成单词高亮。

优先考虑做 vocab_highlight 的词：
1. 单词本身有明显门槛，但查词典就能直接懂，如较低频形容词、动词、学术/科普常见词。
2. 这不是固定搭配核心，也不需要额外语境解释。
3. 读者第一次看到时大概率会卡一下，但不值得单独写 gloss。

不标：
- 低价值词：series、review、site、this、that、time、day 等
- 无理解障碍的普通词：powerful、former、shortage、expert、landscape 等
- 常见新闻词和透明词：ban、powerful、democratic、erasing、waging 等默认不标
- 常见生活短语：gets up、goes to bed、catches the bus 等
- 普通专名：Andrew、Britain、London 等一般人名/国家名/地名默认不标；只有缺少解释会影响理解时才考虑 PhraseGloss.proper_noun
- 不要把普通形容词、描述词、一般抽象名词标成高价值词
- 已经有 phrase_gloss / context_gloss 时，不要再给其中的单词单独做 vocab_highlight

优先级：
1. 先选 PhraseGloss / ContextGloss。
2. 只有前两者都不需要时，才考虑 VocabHighlight。
3. 同一句里宁可少量高价值标注，也不要堆满简单词。

示例：
- "scored 100 per cent" -> phrase_gloss
- "rendered"（表示“把画面呈现出来”）-> context_gloss
- "dexterous" / "tactile" / "refugee" -> vocab_highlight
- "powerful" / "ban" -> 不标

""".strip()

def build_vocabulary_prompt(deps: VocabularyAgentDeps) -> str:
    return build_agent_prompt(
        strategy_sections=build_prompt_sections(deps.prompt_strategy),
        examples=deps.examples,
        sentences=deps.sentences,
    )


@lru_cache(maxsize=1)
def get_vocabulary_agent() -> Agent[VocabularyAgentDeps, VocabularyDraft]:
    return Agent[VocabularyAgentDeps, VocabularyDraft](
        model=None,
        output_type=VocabularyDraft,
        deps_type=VocabularyAgentDeps,
        instructions=VOCABULARY_INSTRUCTIONS,
        name="vocabulary_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

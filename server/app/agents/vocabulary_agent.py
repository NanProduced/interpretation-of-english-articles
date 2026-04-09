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
5. 追求高价值、低噪音，不追求覆盖率。简单日常短文可以只有 0-2 个标注。
6. 需要考虑前端页面的渲染效果，标注数量要视文章长度而定。太多或太少都会影响用户体验。

三个组件的分工：
1. ContextGloss：词典义在当前语境下不够或会误导理解时使用。如果重点只是固定搭配整体义，优先用 PhraseGloss。
2. PhraseGloss：需要整体解释的多词表达（固定搭配、短语动词、术语）。单个词仅在确实需要整体解释的术语/专名/复合词时使用。
3. VocabHighlight：用户可能不认识、但查词典就能直接理解的单词。不需要额外释义，释义由词典 API 提供。

不标：
- 低价值词：series、review、site、this、that、time、day 等
- 无理解障碍的普通词：powerful、former、shortage、expert、landscape 等
- 常见生活短语：gets up、goes to bed、catches the bus 等
- 普通专名：Andrew、Britain、London 等一般人名/国家名/地名默认不标；只有缺少解释会影响理解时才考虑 PhraseGloss.proper_noun
- 不要为了分布到全文而强行找点
- 不要把普通形容词、描述词、一般抽象名词标成高价值词

【示例 1：ContextGloss】
句子："The visuals rendered the ancient world far more vivid than earlier documentaries."
输出：
- type: context_gloss, sentence_id: s1, text: rendered
- gloss: 这里表示"把画面呈现出来"
- reason: 不是普通的技术义"渲染"，而是强调视觉呈现效果

【示例 2：PhraseGloss】
句子："The documentary scored 100 per cent on Rotten Tomatoes."
输出：
- type: phrase_gloss, sentence_id: s1, text: scored 100 per cent
- phrase_type: collocation, zh: 获得百分之百好评

【示例 3：不标】
句子："He gets up at six and catches the bus to work."
→ 不产出，表达基础、词典义直接可懂。

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

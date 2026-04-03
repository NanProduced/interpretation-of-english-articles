"""Vocabulary agent for V3 workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import VocabularyDraft
from app.services.analysis.example_strategy import ExampleEntry
from app.services.analysis.prompt_strategy import PromptStrategy


@dataclass
class VocabularyAgentDeps:
    """Vocabulary agent 依赖。"""

    sentences: list[dict[str, object]]
    prompt_strategy: PromptStrategy
    examples: list[ExampleEntry] = field(default_factory=list)


VOCABULARY_INSTRUCTIONS = """
你是一名英语阅读分析标注器，专注词汇维度标注。

任务：为英文句子生成 vocab_highlight、phrase_gloss、context_gloss 标注。

【核心原则】
1. schema 已经约束输出结构；你只需要决定哪些点真正值得标。
2. 所有锚点文本都必须直接摘自对应句子，不能改写。
3. 所有中文字字段都要写自然中文。
4. 不确定时不标，不猜；不补背景知识，不输出 schema 之外的内容。
5. baseline 追求高价值、低噪音、可读性，不追求覆盖率。

【组件边界】
1. VocabHighlight 只用于单个英文词；用于值得提醒、但不需要额外释义的高价值单词。
2. PhraseGloss 用于需要整体解释的多词表达；单个词只允许在确实需要整体解释的术语、专名或复合词场景下出现。
3. ContextGloss 用于词典义不足以解释当前语境的词或表达；如果重点只是固定搭配整体义，优先使用 PhraseGloss。

【标注优先级】
1. 先考虑 ContextGloss：如果只查词典义会误解句意，优先标它。
2. 再考虑 PhraseGloss：固定搭配、短语动词、术语、真正需要解释的专名。
3. 最后才是 VocabHighlight：高价值但无需额外释义的单词。

【克制规则】
1. 简单日常短文可以只有 0 到 2 个词汇类标注。
2. 常见生活短语如 gets up、goes to bed、catches the bus 通常不标。
3. 一般人名、国家名、机构名、地名默认不标；只有缺少解释会影响理解时，才考虑 PhraseGloss.proper_noun。
4. 不要为了分布到全文而强行找点。
5. 不要把普通单个形容词、普通描述词、一般抽象名词标成高价值词。

【负例提示】
1. 不要标 series、review、site、this、that、time、day 这类低价值词。
2. 不要标 powerful、former、shortage、expert、landscape 这类在当前语境下并未形成理解障碍的普通词。
3. 不要把 Andrew、Britain、London 这类普通专名直接标成 proper_noun。

【Few-shot 示例 1：ContextGloss】
句子："The visuals rendered the ancient world far more vivid than earlier documentaries."
输出：
- type: context_gloss, sentence_id: s1, text: rendered, gloss: 这里表示“把画面呈现出来”, reason: 不是普通的技术义“渲染”，而是强调视觉呈现效果

【Few-shot 示例 2：PhraseGloss】
句子："The documentary scored 100 per cent on Rotten Tomatoes."
输出：
- type: phrase_gloss, sentence_id: s1, text: scored 100 per cent, phrase_type: collocation, zh: 获得百分之百好评

【Few-shot 示例 3：不要标】
句子："He gets up at six and catches the bus to work."
输出：
- 这句可以不做任何词汇类标注，因为表达基础、词典义直接可懂。

【输出前自检】
1. 每个 annotation 都必须真正帮助读懂文章，而不是为了凑数量。
2. 所有锚点文本必须能在对应句子里直接找到。
3. 如果一个点只是普通专名或普通常用词，默认不标。
4. baseline 下 exam_tags 只是附加信息，不能因为“像考试词”就强行标注。
""".strip()


def _render_strategy(strategy: PromptStrategy) -> list[str]:
    lines = [
        f"- reading_goal: {strategy.reading_goal}",
        f"- reading_variant: {strategy.reading_variant}",
    ]
    if strategy.annotation_style:
        lines.append(f"- annotation_style: {strategy.annotation_style}")
    if strategy.vocabulary_policy:
        lines.append(f"- vocabulary_policy: {strategy.vocabulary_policy}")
    if strategy.vocabulary_policy == "high_value_only":
        lines.append("- 执行方式: 只标高价值词，宁可漏标，也不要因为像考试词而凑数量。")
    elif strategy.vocabulary_policy == "exam_priority":
        lines.append("- 执行方式: 可适度提高考试核心词优先级，但仍避免低价值噪音。")
    elif strategy.vocabulary_policy == "academic_priority":
        lines.append("- 执行方式: 优先关注术语和学术语境中的关键表达。")
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


def build_vocabulary_prompt(deps: VocabularyAgentDeps) -> str:
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

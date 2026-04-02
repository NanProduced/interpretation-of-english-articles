"""Vocabulary agent for V3 workflow.

负责 vocab_highlight、phrase_gloss、context_gloss 三类词汇维度标注。
设计原则：
- 不负责语法说明、长难句拆解、逐句翻译
- 允许漏标，不允许大面积低价值误标
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import VocabularyDraft


@dataclass
class VocabularyAgentDeps:
    """Vocabulary agent 依赖。"""
    sentences: list[dict[str, object]]


VOCABULARY_INSTRUCTIONS = """
你是一名英语阅读分析标注器，专注词汇维度标注。

任务：为英文句子生成 vocab_highlight、phrase_gloss、context_gloss 标注。

【核心原则】
1. schema 已经约束输出结构；你只需要决定"哪些点值得标"。
2. 所有锚点文本都必须直接摘自对应句子，不能改写。
3. 所有中文字字段都要写自然中文。
4. 不确定时不标，不猜；不补背景知识，不输出 schema 之外的内容。

【内容优先级】
1. 优先标词典义不足以解释当前语境的词或短语。
2. 再标固定搭配、短语动词、术语、专有名词。
3. 最后才是确实值得提醒的考试词。

【组件使用】
1. VocabHighlight 只用于单词；只选词并给 exam_tags，不写释义。
2. PhraseGloss 用于固定搭配、短语动词、术语、专有名词或复合表达。
3. ContextGloss 只在词典义不足以解释当前语境时使用；如果只看词典释义会误解句意，优先考虑 ContextGloss。

【分布原则】
1. 标注要分布到全文，不要只集中在开头几句。
2. 词汇/短语类标注通常多于语法点。
3. 不要标低价值词（如 series / review / this / that / powerful / former / shortage）。
4. 不要把普通单个形容词误做 PhraseGloss。

【反例】
1. 不要标 series / review / site / this / that 这类低价值词。
2. 不要标 powerful / former / shortage 这类仅有一般描述作用、并未形成理解障碍的普通词。
3. 不要把普通单个形容词误做 PhraseGloss。

【Few-shot 示例 1：ContextGloss】
句子："The visuals rendered the ancient world far more vivid than earlier documentaries."
输出：
- type: context_gloss, sentence_id: s1, text: rendered, gloss: 这里表示"把画面呈现出来", reason: 不是普通的技术义"渲染"，而是强调视觉呈现效果

【Few-shot 示例 2：PhraseGloss】
句子："The documentary scored 100 per cent on Rotten Tomatoes."
输出：
- type: phrase_gloss, sentence_id: s1, text: scored 100 per cent, phrase_type: collocation, zh: 获得百分之百好评

【Few-shot 示例 3：VocabHighlight】
句子："The biggest constitutional crisis is enveloping the British monarchy."
输出：
- type: vocab_highlight, sentence_id: s1, text: constitutional, exam_tags: [cet]

【输出前自检】
1. 每个 annotation 都必须真正帮助读懂文章，而不是为了凑数量。
2. 所有锚点文本必须能在对应句子里直接找到。
3. 如果一个点只适合词典查义，不要强行写成 ContextGloss。
""".strip()


def build_vocabulary_prompt(deps: VocabularyAgentDeps) -> str:
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

"""Grammar agent for V3 workflow.

负责 grammar_note、sentence_analysis 两类结构维度标注。
设计原则：
- 不负责词汇标注、词典查语、逐句翻译
- 优先覆盖显著复杂句，不追求数量
- sentence_analysis.chunks 降级为可选增强字段
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.drafts import GrammarDraft


@dataclass
class GrammarAgentDeps:
    """Grammar agent 依赖。"""
    sentences: list[dict[str, object]]


GRAMMAR_INSTRUCTIONS = """
你是一名英语阅读分析标注器，专注结构维度标注。

任务：为英文句子生成 grammar_note、sentence_analysis 标注。

【核心原则】
1. schema 已经约束输出结构；你只需要决定"哪些点值得标"。
2. 所有锚点文本都必须直接摘自对应句子，不能改写。
3. 所有中文字字段都要写自然中文。
4. 不确定时不标，不猜；不补背景知识，不输出 schema 之外的内容。

【内容优先级】
1. 优先标真正影响理解的复杂句结构。
2. 句子结构独特或容易造成理解障碍的语法现象优先。

【组件使用】
1. GrammarNote 只讲一个清晰语法点；多段锚点只在确实需要时使用。
2. SentenceAnalysis 只用于真正值得拆解的复杂句（嵌套从句或复杂并列结构）。
   - analysis_zh 要说明"先看哪一部分、难点在哪里"。
   - chunks 为可选增强字段，若模型产出高质量 chunks 则保留。

【分布原则】
1. 标注要分布到全文，不要只集中在开头几句。
2. 语法点通常多于长难句拆解。
3. 长文通常至少应覆盖 1 到 2 个最值得讲的复杂句。
4. 不要把所有精力都用在词和短语上；如果全文只有词汇类标注、几乎没有 grammar_note 或 sentence_analysis，通常说明选点过于保守。

【反例】
1. 不要把简单陈述句强行做 SentenceAnalysis。
2. 不要用大量 PhraseGloss 替代本该出现的 SentenceAnalysis 或 GrammarNote。

【Few-shot 示例 1：GrammarNote】
句子："Not only did the policy raise costs, but it also reduced supply."
输出：
- type: grammar_note, sentence_id: s1, spans: [{"text":"Not only","role":"trigger"},{"text":"did","role":"aux"},{"text":"but","role":"conjunction"}], label: not only...but... 倒装, note_zh: Not only 位于句首时，前半句通常触发部分倒装；but 引出并列补充信息。

【Few-shot 示例 2：SentenceAnalysis】
句子："They recognize that sustainable success requires a fundamental rethinking of core business models."
输出：
- type: sentence_analysis, sentence_id: s1, label: 主句加宾语从句, analysis_zh: 先抓主句 They recognize，再看 that 引导的宾语从句。宾语从句核心是 sustainable success requires a fundamental rethinking，最后的 of core business models 说明 rethinking 的对象。

【输出前自检】
1. 每个 annotation 都必须真正帮助读懂文章，而不是为了凑数量。
2. 所有锚点文本必须能在对应句子里直接找到。
3. 长文里如果一个复杂句都没拆，先检查自己是不是过度保守。
""".strip()


def build_grammar_prompt(deps: GrammarAgentDeps) -> str:
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
def get_grammar_agent() -> Agent[GrammarAgentDeps, GrammarDraft]:
    return Agent[GrammarAgentDeps, GrammarDraft](
        model=None,
        output_type=GrammarDraft,
        deps_type=GrammarAgentDeps,
        instructions=GRAMMAR_INSTRUCTIONS,
        name="grammar_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

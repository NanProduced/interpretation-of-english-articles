from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.analysis import AnnotationOutput


@dataclass
class AnnotationAgentDeps:
    sentences: list[dict[str, object]]


ANNOTATION_INSTRUCTIONS = """
你是一名英语阅读分析标注器，帮助中文用户快速读懂英文文章。

任务：
1. 生成 annotations
2. 为每个 sentence 生成中文翻译，且句间翻译保持连贯

【核心原则】
1. schema 已经约束输出结构；你只需要决定“哪些点值得标”。
2. 所有锚点文本都必须直接摘自对应句子，不能改写。
3. 所有中文字段都要写自然中文。
4. 不确定时不标，不猜；不补背景知识，不输出 schema 之外的内容。

【内容优先级】
1. 优先标真正影响理解的复杂句结构。
2. 优先标词典义不足以解释当前语境的词或短语。
3. 再标固定搭配、短语动词、术语、专有名词。
4. 最后才是确实值得提醒的考试词。

【组件使用】
1. VocabHighlight 只用于单词；只选词并给 exam_tags，不写释义。
2. PhraseGloss 用于固定搭配、短语动词、术语、专有名词或复合表达。
3. ContextGloss 只在词典义不足以解释当前语境时使用；如果只看词典释义会误解句意，优先考虑 ContextGloss。
4. GrammarNote 只讲一个清晰语法点；多段锚点只在确实需要时使用。
5. SentenceAnalysis 只用于真正值得拆解的复杂句；analysis_zh 要说明“先看哪一部分、难点在哪里”。

【分布原则】
1. 标注要分布到全文，不要只集中在开头几句。
2. 词汇/短语类标注通常多于语法点。
3. 语法点通常多于长难句拆解。
4. 长文中应优先覆盖每个有明显难点的段落。
5. 如果全文只有词汇类标注、几乎没有 grammar_note 或 sentence_analysis，通常说明你选点过于保守。
6. 长文通常至少应覆盖 1 到 2 个最值得讲的复杂句；不要把所有精力都用在词和短语上。

【反例】
1. 不要标 series / review / site / this / that 这类低价值词。
2. 不要标 powerful / former / shortage 这类仅有一般描述作用、并未形成理解障碍的普通词。
3. 不要把普通单个形容词误做 PhraseGloss。
4. 不要把简单陈述句强行做 SentenceAnalysis。
5. 不要用大量 PhraseGloss 替代本该出现的 SentenceAnalysis 或 GrammarNote。

【Few-shot 示例 1：ContextGloss】
句子："The visuals rendered the ancient world far more vivid than earlier documentaries."
输出片段：
- {"type":"context_gloss","sentence_id":"s1","text":"rendered","gloss":"这里表示“把画面呈现出来”","reason":"不是普通的技术义“渲染”，而是强调视觉呈现效果"}

【Few-shot 示例 2：GrammarNote】
句子："Not only did the policy raise costs, but it also reduced supply."
输出片段：
- {"type":"grammar_note","sentence_id":"s1","spans":[{"text":"Not only","role":"trigger"},{"text":"did","role":"aux"},{"text":"but","role":"conjunction"}],"label":"not only...but... 倒装","note_zh":"Not only 位于句首时，前半句通常触发部分倒装；but 引出并列补充信息。"}

【Few-shot 示例 3：SentenceAnalysis】
句子："They recognize that sustainable success requires a fundamental rethinking of core business models."
输出片段：
- {"type":"sentence_analysis","sentence_id":"s1","label":"主句加宾语从句","analysis_zh":"先抓主句 They recognize，再看 that 引导的宾语从句。宾语从句核心是 sustainable success requires a fundamental rethinking，最后的 of core business models 说明 rethinking 的对象。","chunks":[{"order":1,"label":"主语","text":"They"},{"order":2,"label":"谓语","text":"recognize"},{"order":3,"label":"that 宾语从句","text":"that sustainable success requires a fundamental rethinking"},{"order":4,"label":"of 介词短语","text":"of core business models"}]}

【Few-shot 示例 4：PhraseGloss】
句子："The documentary scored 100 per cent on Rotten Tomatoes."
输出片段：
- {"type":"phrase_gloss","sentence_id":"s1","text":"scored 100 per cent","phrase_type":"collocation","zh":"获得百分之百好评"}

【输出前自检】
1. 每个 annotation 都必须真正帮助读懂文章，而不是为了凑数量。
2. 所有锚点文本必须能在对应句子里直接找到。
3. sentence_translations 必须覆盖所有句子。
4. 如果一个点只适合词典查义，不要强行写成 ContextGloss 或 SentenceAnalysis。
5. 长文里如果一个复杂句都没拆，先检查自己是不是过度保守。

""".strip()
def build_annotation_prompt(deps: AnnotationAgentDeps) -> str:
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
def get_annotation_agent() -> Agent[AnnotationAgentDeps, AnnotationOutput]:
    return Agent[AnnotationAgentDeps, AnnotationOutput](
        model=None,
        output_type=AnnotationOutput,
        deps_type=AnnotationAgentDeps,
        instructions=ANNOTATION_INSTRUCTIONS,
        name="annotation_agent",
        retries=2,
        output_retries=2,
        instrument=False,
    )

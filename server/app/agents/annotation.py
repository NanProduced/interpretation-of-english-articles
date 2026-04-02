from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.analysis import AnnotationOutput


@dataclass
class AnnotationAgentDeps:
    sentences: list[dict[str, object]]


ANNOTATION_INSTRUCTIONS = """
你是一名英语语言专家，帮助中文用户读懂英文文章。

任务：为文章生成标注（annotations）和逐句中文翻译（sentence_translations）。

## 通用规则
1. 所有 text / spans[].text / chunks[].text 必须是 sentence_id 对应句子的精确子串，直接复制原文。
2. 所有中文字段（gloss / reason / note_zh / analysis_zh / zh / translation_zh）必须输出中文。
3. sentence_translations 必须覆盖全部句子，句间翻译要连贯。
4. 宁少勿滥，不为凑数量而标注。

## 分布参考（软约束）
- 标注应分散到全文，后半段应与前半段有大致相当的标注密度。

## Few-shot 示例

### ✓ VocabHighlight 正确
s7: "He also directed the blockbuster movie Jurassic Park."
→ "type":"vocab_highlight","sentence_id":"s7","text":"blockbuster","exam_tags":["CET-6","IELTS"]

### ✗ VocabHighlight 错误（基础词不标）
s4: "It has powerful figures from Hollywood behind it."
→ powerful 是高中基础词，intermediate 读者已认识，跳过。

### ✓ PhraseGloss 正确
s17: "...the asteroid impact event that killed off the dinosaurs."
→ "type":"phrase_gloss","sentence_id":"s17","text":"killed off","phrase_type":"phrasal_verb","zh":"使灭绝、彻底消灭"

### ✗ PhraseGloss 错误（单词不是短语）
s16: "...the most iconic dinosaurs of all time"
→ iconic 是单个词，应使用 VocabHighlight，不能用 PhraseGloss。

### ✓ ContextGloss
s19: "the geology and meteorology are powerfully rendered"
→ "type":"context_gloss","sentence_id":"s19","text":"rendered","gloss":"这里表示'被有力地呈现、描绘出来'","reason":"rendered 常见义为'渲染（技术）'或'提交'，但此处影评语境指视觉呈现效果，词典第一义项会导致误解。"

### ✓ GrammarNote（多段锚点）
s1: "Not only did the policy raise costs, but it also reduced supply."
→ {{"type":"grammar_note","sentence_id":"s1","spans":["text":"Not only","role":"倒装触发词","text":"did","role":"助动词前置",{{"text":"but","role":"并列连词"}],"label":"not only...but also 倒装","note_zh":"Not only 位于句首时触发部分倒装（助动词 did 提前）；but it also 引出并列补充信息。"}}

### ✓ SentenceAnalysis
s10: "The four episodes document how the earliest dinosaurs developed, survived for millions of years, and became extinct."
→ {{"type":"sentence_analysis","sentence_id":"s10","label":"how 宾语从句 + 三重并列谓语","analysis_zh":"先抓主干 The four episodes document...（四集纪录了……）。how 引导宾语从句，从句内三个并列谓语按时间线展开：developed（演化）→ survived（存活）→ became extinct（灭绝）。难点在于并列谓语跨度长，容易漏读第三个。","chunks":["order":1,"label":"主语","text":"The four episodes","order":2,"label":"谓语","text":"document",{{"order":3,"label":"how 宾语从句","text":"how the earliest dinosaurs developed, survived for millions of years, and became extinct"}]}}

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

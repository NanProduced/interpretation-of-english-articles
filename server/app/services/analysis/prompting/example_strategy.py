"""Example strategy for V3 workflow.

负责 example selection。
设计原则：
- baseline = 最少 few-shot
- 后续可通过 RAG 注入 dynamic few-shot
- 不影响 baseline 稳定性
- 示例要体现 variant 的差异化方向
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas.internal.execution_plan import GoalExecutionPlan


@dataclass
class ExampleEntry:
    """Example 条目。"""
    example_type: Literal["vocab", "phrase", "context", "grammar", "sentence_analysis", "translation"]
    sentence_text: str
    output_fragment: str


@dataclass
class ExampleStrategy:
    """Example 策略。"""
    examples: list[ExampleEntry]
    selection_mode: Literal["baseline", "rag", "manual"] = "baseline"


# --- BEGINNER EXAMPLES ---
BEGINNER_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="vocab",
        sentence_text="The weather was very pleasant today.",
        output_fragment='{"type": "vocab_highlight", "text": "pleasant"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="He decided to give up smoking.",
        output_fragment='{"type": "phrase_gloss", "text": "give up", "phrase_type": "phrasal_verb", "zh": "放弃；戒掉。日常很常用，比如 give up smoking（戒烟）、give up trying（放弃尝试）"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="She takes care of her little brother every day.",
        output_fragment='{"type": "phrase_gloss", "text": "takes care of", "phrase_type": "collocation", "zh": "照顾；照看。日常超常用，比如 take care of yourself（照顾好自己）"}',
    ),
]

BEGINNER_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="The boy who is wearing a red hat is my brother.",
        output_fragment='{"type": "sentence_analysis", "label": "拆解长句", "analysis_zh": "主干是 The boy is my brother（那个男孩是我弟弟）。中间 who is wearing a red hat 是补充说明男孩的，告诉我们是\"戴红帽子的\"那个男孩。先看主干，再看中间的补充说明。", "chunks": [{"order": 1, "label": "主干主语", "text": "The boy"}, {"order": 2, "label": "补充说明", "text": "who is wearing a red hat"}, {"order": 3, "label": "主干谓语宾语", "text": "is my brother"}]}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="He gave up smoking last year.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "gave up"}, {"text": "smoking"}], "label": "give up + 动词-ing", "note_zh": "give up 后面跟动词的 -ing 形式，表示\"放弃做某事\"。日常很常用，比如 I gave up eating junk food（我戒掉了垃圾食品）。"}',
    ),
]

BEGINNER_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The boy who is wearing a red hat is my brother.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "那个戴着红帽子的男孩是我的弟弟。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="Having finished the report, she left the office.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "（在）完成了报告之后，她离开了办公室。"}',
    ),
]

# --- INTERMEDIATE EXAMPLES ---
INTERMEDIATE_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="phrase",
        sentence_text="The documentary scored 100 per cent on Rotten Tomatoes.",
        output_fragment='{"type": "phrase_gloss", "text": "scored 100 per cent", "phrase_type": "collocation", "zh": "获得百分之百的评分"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The government has been slow to address the issue.",
        output_fragment='{"type": "context_gloss", "text": "address", "gloss": "处理；应对", "reason": "address 常见义为\"地址\"或\"演讲\"，此处是\"着手处理问题\"的语境义"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The visuals rendered the ancient world far more vivid than earlier documentaries.",
        output_fragment='{"type": "context_gloss", "text": "rendered", "gloss": "把…呈现出来", "reason": "render 常见义为\"使得\"或\"渲染\"，此处表示视觉上把远古世界呈现出来"}',
    ),
]

INTERMEDIATE_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="Not only did the policy raise costs, but it also reduced supply.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "Not only"}, {"text": "did"}, {"text": "but"}], "label": "not only...but also 倒装结构", "note_zh": "Not only 放在句首时触发部分倒装（did 提前）。阅读时先理解前半句主干，再接上 but 后面的补充。"}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="Had the company invested earlier, it would have dominated the market.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "Had"}, {"text": "would have"}], "label": "虚拟条件句倒装", "note_zh": "Had 开头等于 If it had，是虚拟条件句的倒装形式，表示与过去事实相反的假设。would have dominated 是对应的虚拟结果。"}',
    ),
]

INTERMEDIATE_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The visuals rendered the ancient world far more vivid than earlier documentaries.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "这些画面把远古世界呈现得比以往的纪录片生动得多。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="The policy, while well-intentioned, ended up hurting the very people it was meant to help.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "这项政策虽然出发点是好的，最终却伤害了它本想帮助的人。"}',
    ),
]

# --- INTENSIVE EXAMPLES ---
INTENSIVE_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="context",
        sentence_text="The architect\'s design was a subtle nod to brutalism.",
        output_fragment='{"type": "context_gloss", "text": "nod to", "gloss": "致敬；呼应", "reason": "nod 原指点头，此处修辞性地表示设计上对某种风格的隐喻性致敬，体现了选词的委婉与深度"}',
    ),
    ExampleEntry(
        example_type="vocab",
        sentence_text="His arguments were both pellucid and persuasive.",
        output_fragment='{"type": "vocab_highlight", "text": "pellucid"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The policy was less a reform than a cosmetic tweak.",
        output_fragment='{"type": "context_gloss", "text": "cosmetic", "gloss": "表面上的；装点门面的", "reason": "cosmetic 本义\"化妆品的\"，此处隐喻政策改动只是表面功夫，未触及实质。选词本身带有讽刺意味"}',
    ),
]

INTENSIVE_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="Rarely has a discovery so fundamentally altered our understanding of the cosmos.",
        output_fragment='{"type": "sentence_analysis", "label": "否定副词前置与修辞强调", "analysis_zh": "Rarely 前置触发倒装，强调\"罕见性\"。句子信息密度高，通过 altered our understanding 建立了发现与认知的关联。这种句式常用于学术或正式论述中，以增强语气。", "chunks": [{"order": 1, "label": "强调起点", "text": "Rarely has a discovery"}, {"order": 2, "label": "核心动作", "text": "so fundamentally altered"}, {"order": 3, "label": "受影响对象", "text": "our understanding of the cosmos"}]}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="That such a modest proposal provoked outrage reveals more about the audience than the content.",
        output_fragment='{"type": "sentence_analysis", "label": "名词性从句前置与信息焦点", "analysis_zh": "That 引导的主语从句前置，将\"引发愤怒\"这一事实本身作为主语，使句子焦点自然落在 reveals 上——作者刻意将\"令人意外\"的信息结构化，暗示愤怒反应的不合理。这种结构比 \"It reveals...that...\" 更有力，因为主语从句本身承载了作者的判断。", "chunks": [{"order": 1, "label": "事实主语", "text": "That such a modest proposal provoked outrage"}, {"order": 2, "label": "核心判断", "text": "reveals more about the audience than the content"}]}',
    ),
]

INTENSIVE_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="Rarely has a discovery so fundamentally altered our understanding of the cosmos.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "很少有一项发现能如此从根本上改变我们对宇宙的认知。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="The policy was less a reform than a cosmetic tweak.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "这项政策与其说是改革，不如说是装点门面。"}',
    ),
]


def get_vocabulary_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 vocabulary agent 的 example 策略。"""
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)
    
    if plan.variant_id == "beginner_reading":
        examples = BEGINNER_VOCABULARY_EXAMPLES
    elif plan.variant_id == "intensive_reading":
        examples = INTENSIVE_VOCABULARY_EXAMPLES
    else:
        examples = INTERMEDIATE_VOCABULARY_EXAMPLES
        
    return ExampleStrategy(examples=examples, selection_mode="baseline")


def get_grammar_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 grammar agent 的 example 策略。"""
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)
        
    if plan.variant_id == "beginner_reading":
        examples = BEGINNER_GRAMMAR_EXAMPLES
    elif plan.variant_id == "intensive_reading":
        examples = INTENSIVE_GRAMMAR_EXAMPLES
    else:
        examples = INTERMEDIATE_GRAMMAR_EXAMPLES
        
    return ExampleStrategy(examples=examples, selection_mode="baseline")


def get_translation_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 translation agent 的 example 策略。"""
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)
        
    if plan.variant_id == "beginner_reading":
        examples = BEGINNER_TRANSLATION_EXAMPLES
    elif plan.variant_id == "intensive_reading":
        examples = INTENSIVE_TRANSLATION_EXAMPLES
    else:
        examples = INTERMEDIATE_TRANSLATION_EXAMPLES
        
    return ExampleStrategy(examples=examples, selection_mode="baseline")

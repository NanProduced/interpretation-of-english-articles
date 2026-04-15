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


# --- GAOKAO EXAMPLES ---
GAOKAO_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="vocab",
        sentence_text="The government has adopted new measures to protect the environment.",
        output_fragment='{"type": "vocab_highlight", "text": "adopted"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="She is looking forward to hearing from her pen pal.",
        output_fragment='{"type": "phrase_gloss", "text": "looking forward to", "phrase_type": "collocation", "zh": "期待；盼望。注意 to 是介词，后面接动词-ing 形式：look forward to doing sth. 期待做某事"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="The team carried out the experiment successfully.",
        output_fragment='{"type": "phrase_gloss", "text": "carried out", "phrase_type": "phrasal_verb", "zh": "执行；实施。高考常考短语，如 carry out a plan/experiment/survey"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The government has been slow to address the issue of air pollution.",
        output_fragment='{"type": "context_gloss", "text": "address", "gloss": "处理；应对", "reason": "address 常见义为\"地址\"或\"演讲\"，此处作动词表示\"着手处理问题\"。高考词义猜测题常考这类熟词僻义，解题关键是看词性和上下文：此处后面接了 the issue（问题），说明是动词\"处理\""}',
    ),
]

GAOKAO_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="The book that was written by him has become a bestseller.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "that"}, {"text": "was written"}], "label": "定语从句", "note_zh": "that 引导定语从句修饰 the book。that 在从句中作主语，指代先行词 the book，所以从句用被动语态 was written。高考语法填空常考：① 判断用哪个关系词（that/which/who/where） ② 从句的时态和语态。"}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="Inspired by the speech, the students decided to start their own project.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "Inspired"}, {"text": "decided"}], "label": "过去分词作状语", "note_zh": "Inspired by the speech 是过去分词短语作原因状语，逻辑主语是 the students（学生被演讲激励）。过去分词表被动关系，说明主语是动作的承受者。高考语法填空常考：判断用现在分词（-ing，表主动）还是过去分词（-ed，表被动）。"}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="The research conducted by scientists from different countries shows that climate change has affected the lives of millions of people.",
        output_fragment='{"type": "sentence_analysis", "label": "过去分词后置定语 + 宾语从句", "analysis_zh": "主干：The research shows that...（这项研究表明……）。conducted by scientists from different countries 是过去分词短语作后置定语，修饰 the research，说明是\"来自不同国家的科学家所进行的\"研究。that 引导宾语从句，作 shows 的宾语，说明研究的结果。高考阅读中遇到长句，先找主干（谁做了什么），再看修饰成分。", "chunks": [{"order": 1, "label": "主干主语", "text": "The research"}, {"order": 2, "label": "后置定语", "text": "conducted by scientists from different countries"}, {"order": 3, "label": "主干谓语", "text": "shows"}, {"order": 4, "label": "宾语从句", "text": "that climate change has affected the lives of millions of people"}]}',
    ),
]

GAOKAO_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The book that was written by him has become a bestseller.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "他写的那本书已经成为了一本畅销书。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="Inspired by the speech, the students decided to start their own project.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "（被）演讲所激励，学生们决定开始他们自己的项目。"}',
    ),
]


# --- CET EXAMPLES ---
CET_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="vocab",
        sentence_text="The economic growth has slowed down significantly this year.",
        output_fragment='{"type": "vocab_highlight", "text": "economic"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="Rising temperatures account for the decline in crop yields.",
        output_fragment='{"type": "phrase_gloss", "text": "account for", "phrase_type": "collocation", "zh": "占……比例；是……的原因。同义表达：make up, explain, be responsible for"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="The new policy has contributed to a significant reduction in emissions.",
        output_fragment='{"type": "phrase_gloss", "text": "contributed to", "phrase_type": "collocation", "zh": "促成；有助于。同义表达：led to, resulted in, brought about"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The government has been slow to address the issue of climate change.",
        output_fragment='{"type": "context_gloss", "text": "address", "gloss": "处理；应对", "reason": "address 常见义为\"地址\"或\"演讲\"，此处作动词表示\"着手处理问题\"。四六级选项常用该词的常见义设置干扰，注意根据上下文判断词义"}',
    ),
]

CET_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="The study, which was conducted by researchers from Harvard, found that regular exercise can reduce stress.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "which"}, {"text": "found"}], "label": "非限制性定语从句", "note_zh": "which 引导非限制性定语从句，补充说明 the study。快速阅读时可先跳过逗号之间的从句，抓住主干 The study found that...（研究发现……）"}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="Influenced by social media, young people tend to spend more time online.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "Influenced"}, {"text": "tend"}], "label": "过去分词作状语", "note_zh": "Influenced by social media 是过去分词短语作原因状语，表示\"受社交媒体影响\"。快速阅读时，看到句首的过去分词，先找主语和谓语（young people tend to...），再回头看分词短语补充的信息"}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="A recent study conducted by the University of Oxford has found that people who regularly engage in physical activity are less likely to develop heart disease.",
        output_fragment='{"type": "sentence_analysis", "label": "后置定语 + 宾语从句 + 定语从句", "analysis_zh": "主干：A recent study has found that...（一项最新研究发现……）。conducted by the University of Oxford 是过去分词短语作后置定语修饰 study。that 引导宾语从句，其中 who regularly engage in physical activity 是定语从句修饰 people。主干信息是\"经常锻炼的人更不容易患心脏病\"。在段落匹配题中，这类信息可能被改写为\"physical activity is linked to lower risk of heart disease\"。", "chunks": [{"order": 1, "label": "主干主语", "text": "A recent study"}, {"order": 2, "label": "后置定语", "text": "conducted by the University of Oxford"}, {"order": 3, "label": "主干谓语", "text": "has found"}, {"order": 4, "label": "宾语从句", "text": "that people who regularly engage in physical activity are less likely to develop heart disease"}]}',
    ),
]

CET_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The study, which was conducted by researchers from Harvard, found that regular exercise can reduce stress.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "这项由哈佛大学研究人员进行的研究发现，经常锻炼可以减轻压力。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="Rising temperatures account for the decline in crop yields.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "气温上升是农作物产量下降的原因。（此处 account for 即题目中的 be responsible for）"}',
    ),
]


# --- KAOYAN EXAMPLES ---
KAOYAN_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="context",
        sentence_text="The government has been slow to address the growing crisis.",
        output_fragment='{"type": "context_gloss", "text": "address", "gloss": "处理；应对", "reason": "address 常见义为\"地址\"或\"演讲\"，此处作动词表示\"着手处理\"。考研常通过熟词僻义考察精确理解，解题关键是看词性和上下文：此处后面接了 the growing crisis，说明是动词\"处理\""}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="The policy is problematic in that it fails to consider regional differences.",
        output_fragment='{"type": "phrase_gloss", "text": "in that", "phrase_type": "collocation", "zh": "因为；在于。用于引出具体原因或限定范围，比 because 更正式，常出现在考研阅读的论证结构中"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="The company succeeded by virtue of its early investment in technology.",
        output_fragment='{"type": "phrase_gloss", "text": "by virtue of", "phrase_type": "collocation", "zh": "凭借；由于。用于说明某事成立的原因或依据，比 because of 更正式，考研阅读中常出现在因果论证段落"}',
    ),
    ExampleEntry(
        example_type="vocab",
        sentence_text="The novel approach has attracted widespread attention.",
        output_fragment='{"type": "vocab_highlight", "text": "novel"}',
    ),
]

KAOYAN_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="The approach, which was initially designed for urban areas, has failed to address the needs of rural communities.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "which"}, {"text": "has failed"}], "label": "非限制性定语从句 + 主谓分离", "note_zh": "which 引导非限制性定语从句修饰 the approach，可先跳过。主干是 The approach has failed to address...（这种方法未能解决……）。主语和谓语被从句拆开了，阅读时先跳过逗号之间的从句抓主干"}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="The findings, the researchers argue, challenge the prevailing assumption that economic growth inevitably reduces poverty.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "the researchers argue"}, {"text": "that"}], "label": "插入语 + 同位语从句", "note_zh": "the researchers argue 是插入语，可先跳过。主干是 The findings challenge the assumption（发现挑战了假设）。that 引导同位语从句解释 assumption 的内容。这种\"插入语打断主谓\"的结构在考研文本中很常见"}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="The study suggests that the approach, which was initially designed for urban areas, has failed to address the needs of rural communities, leading researchers to call for a fundamental revision of the policy.",
        output_fragment='{"type": "sentence_analysis", "label": "宾语从句 + 非限制性定语从句 + 分词结果状语", "analysis_zh": "主干：The study suggests that...（研究表明……）。that 引导宾语从句，从句主干是 the approach has failed to address...（这种方法未能解决……）。which was initially designed for urban areas 是非限制性定语从句修饰 approach，可先跳过。leading researchers to call for... 是现在分词作结果状语，表示\"导致研究人员呼吁……\"。这种\"主句 + 宾语从句内嵌定语从句 + 分词状语\"的多层嵌套结构是考研翻译题的高频出题点", "chunks": [{"order": 1, "label": "主干", "text": "The study suggests"}, {"order": 2, "label": "宾语从句主语", "text": "that the approach"}, {"order": 3, "label": "插入的定语从句", "text": "which was initially designed for urban areas"}, {"order": 4, "label": "宾语从句谓语宾语", "text": "has failed to address the needs of rural communities"}, {"order": 5, "label": "分词结果状语", "text": "leading researchers to call for a fundamental revision of the policy"}]}',
    ),
]

KAOYAN_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The approach, which was initially designed for urban areas, has failed to address the needs of rural communities.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "这种方法最初是为城市地区设计的，但未能解决农村社区的需求。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="The findings, the researchers argue, challenge the prevailing assumption that economic growth inevitably reduces poverty.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "研究人员认为，这些发现挑战了经济增长必然减少贫困这一普遍假设。（此处 that 从句解释 assumption 的内容）"}',
    ),
]


# --- TEM EXAMPLES ---
TEM_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="context",
        sentence_text="The old house stood at the end of the lane, its windows like blind eyes staring into nothingness.",
        output_fragment='{"type": "context_gloss", "text": "blind", "gloss": "失明的；无神的", "reason": "blind 常见义为\"盲的\"，此处修饰 windows，通过拟人手法赋予窗户\"失明的眼睛\"的意象，暗示房屋的荒废和死寂。专八常考察对修辞含义的精确理解，需超越字面义体会隐喻效果"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="She found herself between Scylla and Charybdis, unable to please either her employer or her family.",
        output_fragment='{"type": "phrase_gloss", "text": "between Scylla and Charybdis", "phrase_type": "idiom", "zh": "进退两难；腹背受敌。源自希腊神话中两个海怪的故事，文学文本中常用来暗示人物的两难困境，比 between a rock and a hard place 更具文学性和文化底蕴"}',
    ),
    ExampleEntry(
        example_type="vocab",
        sentence_text="The novel\'s evocative prose transports readers to a bygone era.",
        output_fragment='{"type": "vocab_highlight", "text": "evocative"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The politician\'s promise was, at best, a Faustian bargain.",
        output_fragment='{"type": "context_gloss", "text": "Faustian", "gloss": "浮士德式的；为获取利益而出卖灵魂的", "reason": "Faustian 源自德国传说中浮士德与魔鬼的交易，此处隐喻政客的承诺看似诱人实则代价惨重。专八常考察对文化典故的识别和理解"}',
    ),
]

TEM_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="Never had she felt so alone, so utterly abandoned by the world.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "Never"}, {"text": "had she felt"}], "label": "倒装 + 反复", "note_zh": "Never 前置触发倒装，营造紧迫感和戏剧性——读者先被\"从未\"击中，再感受到主语的孤独。so...so... 反复强化情绪的递进，从 alone 到 utterly abandoned，孤独感层层加深。这种倒装+反复的组合是文学文本中常见的情绪渲染手法，专八常考作者意图题"}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="The shadows lengthened, stretched across the empty room like the fingers of some unseen hand.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "lengthened"}, {"text": "stretched"}], "label": "动词并列 + 明喻", "note_zh": "lengthened 和 stretched 两个动词并列，赋予阴影主动性和侵入感——阴影不是被动存在，而是在\"蔓延\"。like the fingers of some unseen hand 是明喻，将阴影比作\"看不见的手指\"，营造不安和神秘氛围。这种动词选择+明喻的组合是文学描写中常见的氛围营造手法"}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="Had she known then what she knows now, she would never have opened that door, would never have stepped into the light that was, in truth, no light at all.",
        output_fragment='{"type": "sentence_analysis", "label": "虚拟倒装 + 反复否定 + 反讽", "analysis_zh": "Had she known 是虚拟条件句倒装，表达与过去事实相反的假设，奠定悔恨基调。would never have...would never have... 反复否定强化不可挽回的遗憾感。that was, in truth, no light at all 是反讽——看似光明实则黑暗，暗示主角被表象蒙蔽。整句通过虚拟+反复+反讽的三重修辞，将悔恨和幻灭推向极致。这种手法在专八阅读中常考作者意图和态度判断", "chunks": [{"order": 1, "label": "虚拟假设", "text": "Had she known then what she knows now"}, {"order": 2, "label": "反复否定一", "text": "she would never have opened that door"}, {"order": 3, "label": "反复否定二", "text": "would never have stepped into the light"}, {"order": 4, "label": "反讽揭示", "text": "that was, in truth, no light at all"}]}',
    ),
]

TEM_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="Never had she felt so alone, so utterly abandoned by the world.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "她从未感到如此孤独，如此被世界彻底遗弃。"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="The shadows lengthened, stretched across the empty room like the fingers of some unseen hand.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "阴影渐渐拉长，如同一只看不见的手的指头般蔓延过空荡荡的房间。（此处 like 明喻将阴影比作手指，营造不安氛围）"}',
    ),
]


# --- IELTS/TOEFL EXAMPLES ---
IELTS_TOEFL_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="phrase",
        sentence_text="The decline in biodiversity has been attributed to habitat loss and climate change.",
        output_fragment='{"type": "phrase_gloss", "text": "has been attributed to", "phrase_type": "collocation", "zh": "被归因于。学术高频搭配，用于说明因果关系。同义表达: result from, stem from, arise from, be caused by"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="The new policy gave rise to widespread criticism.",
        output_fragment='{"type": "phrase_gloss", "text": "gave rise to", "phrase_type": "collocation", "zh": "引起；导致。学术论证常用搭配，用于引出结果。同义表达: lead to, result in, bring about, trigger"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The Chicago school of economics dominated policy-making in the 1980s.",
        output_fragment='{"type": "context_gloss", "text": "school", "gloss": "学派；流派", "reason": "school 常见义为\"学校\"，此处指学术流派。雅思/托福常利用学术义与日常义的差异设置考点，需根据上下文判断：此处后面接了 of economics，说明是\"经济学派\""}',
    ),
    ExampleEntry(
        example_type="vocab",
        sentence_text="The findings facilitate a deeper understanding of the mechanism.",
        output_fragment='{"type": "vocab_highlight", "text": "facilitate"}',
    ),
]

IELTS_TOEFL_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="The factor that contributed most significantly to the decline was habitat loss.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "that"}, {"text": "contributed"}], "label": "限制性定语从句", "note_zh": "that 引导限制性定语从句，限定了是\"哪个\" factor——是导致衰退最显著的那个因素。这类限定信息在雅思 T/F/NG 题中常被改写为判断对象，如果题目说\"Habitat loss was the primary factor\"，答案取决于原文的限定是否精确"}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="The mechanism by which the drug operates has not been fully elucidated.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "by which"}, {"text": "has not been"}], "label": "介词+关系代词 + 被动语态", "note_zh": "by which 引导定语从句修饰 mechanism，说明药物\"通过什么机制\"起作用。has not been fully elucidated 是被动语态，动作执行者被省略（学术界惯例）。被动语态在学术文本中极常见（约 30-40% 的句子），需注意动作执行者是被省略了还是在 by 后面"}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="Although traditional methods have proven effective in certain contexts, the emerging approach offers significant advantages, particularly in terms of efficiency and scalability.",
        output_fragment='{"type": "sentence_analysis", "label": "让步（承认传统方法价值）+ 转折（提出新方法优势）+ 限定（适用范围）", "analysis_zh": "主干：the emerging approach offers significant advantages（新方法具有显著优势）。although 引导让步从句，承认传统方法的价值，为转折做铺垫。particularly in terms of... 限定了优势的适用范围——效率和可扩展性。这句在段落中的功能是提出核心论点并限定适用范围。TOEFL 可能考\"为什么作者提到传统方法的优势？\"（答案：让步，为转折做铺垫）。IELTS 的 T/F/NG 可能将\"新方法在所有方面都优于传统方法\"设为 False（因为原文有 particularly 限定）", "chunks": [{"order": 1, "label": "让步从句", "text": "Although traditional methods have proven effective in certain contexts"}, {"order": 2, "label": "核心主张", "text": "the emerging approach offers significant advantages"}, {"order": 3, "label": "限定范围", "text": "particularly in terms of efficiency and scalability"}]}',
    ),
]

IELTS_TOEFL_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The decline in biodiversity has been attributed to habitat loss and climate change.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "生物多样性的下降被归因于栖息地丧失和气候变化。（此处 has been attributed to 在题目中常被改写为 result from 或 is caused by）"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="Although traditional methods have proven effective in certain contexts, the emerging approach offers significant advantages.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "尽管传统方法在某些情境下已被证明有效，但新兴方法具有显著优势。"}',
    ),
]


# --- ACADEMIC EXAMPLES ---
ACADEMIC_VOCABULARY_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="phrase",
        sentence_text="The results can be attributed to a combination of factors.",
        output_fragment='{"type": "phrase_gloss", "text": "attributed to", "phrase_type": "collocation", "zh": "归因于。学术高频搭配，用于说明因果关系。功能：引出原因或解释"}',
    ),
    ExampleEntry(
        example_type="phrase",
        sentence_text="In terms of methodology, this study adopts a qualitative approach.",
        output_fragment='{"type": "phrase_gloss", "text": "In terms of", "phrase_type": "collocation", "zh": "就……而言；在……方面。学术高频搭配，用于限定讨论范围。功能：话题切换或范围限定"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="The Chicago school of economics has influenced policy-making worldwide.",
        output_fragment='{"type": "context_gloss", "text": "school", "gloss": "学派；流派", "reason": "school 常见义为\"学校\"，此处指学术流派。学术语境中常用来指代具有共同理论框架的学者群体"}',
    ),
    ExampleEntry(
        example_type="context",
        sentence_text="This paper addresses the limitations of previous research.",
        output_fragment='{"type": "context_gloss", "text": "addresses", "gloss": "探讨；处理；应对", "reason": "address 常见义为\"地址\"或\"演讲\"，此处作动词表示\"着手探讨或处理问题\"。学术论文中常用"}',
    ),
    ExampleEntry(
        example_type="vocab",
        sentence_text="The empirical evidence supports our hypothesis.",
        output_fragment='{"type": "vocab_highlight", "text": "empirical"}',
    ),
    ExampleEntry(
        example_type="vocab",
        sentence_text="The theoretical framework provides a basis for analysis.",
        output_fragment='{"type": "vocab_highlight", "text": "framework"}',
    ),
]

ACADEMIC_GRAMMAR_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="grammar",
        sentence_text="The data, which was collected over three years, reveals significant trends.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "which"}, {"text": "reveals"}], "label": "非限制性定语从句", "note_zh": "which 引导非限制性定语从句，补充说明数据的收集时间。快速阅读时可先跳过逗号之间的从句，抓住主干：The data reveals significant trends（数据揭示了显著趋势）。功能：补充信息，不影响主干理解"}',
    ),
    ExampleEntry(
        example_type="grammar",
        sentence_text="It has been suggested that this approach may have limitations.",
        output_fragment='{"type": "grammar_note", "spans": [{"text": "It has been suggested"}, {"text": "may have"}], "label": "形式主语 + 被动语态", "note_zh": "It 是形式主语，真正的主语是 that 从句。has been suggested 是被动语态，动作执行者被省略（学术惯例）。这种结构在学术文本中极常见，用于表达\"有人认为\"或\"研究表明\"，避免直接引用特定研究者。功能：客观陈述，弱化主体"}',
    ),
    ExampleEntry(
        example_type="sentence_analysis",
        sentence_text="Although previous studies have identified these patterns, the underlying mechanisms remain poorly understood, and further research is needed to elucidate the causal relationships.",
        output_fragment='{"type": "sentence_analysis", "label": "让步转折 + 并列论证", "analysis_zh": "这是一个典型的学术论证结构。Although 引导让步从句，承认已有研究的贡献（identified these patterns），为转折做铺垫。主句分两部分：第一部分指出研究空白（mechanisms remain poorly understood），第二部分提出研究需求（further research is needed）。整句功能：定位研究缺口，justify 当前研究的必要性。", "chunks": [{"order": 1, "label": "让步承认", "text": "Although previous studies have identified these patterns"}, {"order": 2, "label": "指出缺口", "text": "the underlying mechanisms remain poorly understood"}, {"order": 3, "label": "提出需求", "text": "and further research is needed to elucidate the causal relationships"}]}',
    ),
]

ACADEMIC_TRANSLATION_EXAMPLES: list[ExampleEntry] = [
    ExampleEntry(
        example_type="translation",
        sentence_text="The empirical evidence suggests that the methodology is robust.",
        output_fragment='{"sentence_id": "s1", "translation_zh": "实证证据表明该方法学是稳健的。（empirical = 实证的，methodology = 方法学，robust = 稳健的——这些是学术论文中的标准术语）"}',
    ),
    ExampleEntry(
        example_type="translation",
        sentence_text="Although these findings are significant, further research is required to validate the causal relationships.",
        output_fragment='{"sentence_id": "s2", "translation_zh": "尽管这些发现具有重要意义，但仍需进一步研究以验证因果关系。（Although 表示让步转折，是学术论证中\"承认局限+提出需求\"的典型结构）"}',
    ),
]


def get_vocabulary_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 vocabulary agent 的 example 策略。"""
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)
    
    if plan.goal_id == "academic":
        examples = ACADEMIC_VOCABULARY_EXAMPLES
    elif plan.variant_id == "beginner_reading":
        examples = BEGINNER_VOCABULARY_EXAMPLES
    elif plan.variant_id == "intensive_reading":
        examples = INTENSIVE_VOCABULARY_EXAMPLES
    elif plan.variant_id == "gaokao":
        examples = GAOKAO_VOCABULARY_EXAMPLES
    elif plan.variant_id == "cet":
        examples = CET_VOCABULARY_EXAMPLES
    elif plan.variant_id == "kaoyan":
        examples = KAOYAN_VOCABULARY_EXAMPLES
    elif plan.variant_id == "tem":
        examples = TEM_VOCABULARY_EXAMPLES
    elif plan.variant_id == "ielts_toefl":
        examples = IELTS_TOEFL_VOCABULARY_EXAMPLES
    else:
        examples = INTERMEDIATE_VOCABULARY_EXAMPLES
        
    return ExampleStrategy(examples=examples, selection_mode="baseline")


def get_grammar_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 grammar agent 的 example 策略。"""
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)
        
    if plan.goal_id == "academic":
        examples = ACADEMIC_GRAMMAR_EXAMPLES
    elif plan.variant_id == "beginner_reading":
        examples = BEGINNER_GRAMMAR_EXAMPLES
    elif plan.variant_id == "intensive_reading":
        examples = INTENSIVE_GRAMMAR_EXAMPLES
    elif plan.variant_id == "gaokao":
        examples = GAOKAO_GRAMMAR_EXAMPLES
    elif plan.variant_id == "cet":
        examples = CET_GRAMMAR_EXAMPLES
    elif plan.variant_id == "kaoyan":
        examples = KAOYAN_GRAMMAR_EXAMPLES
    elif plan.variant_id == "tem":
        examples = TEM_GRAMMAR_EXAMPLES
    elif plan.variant_id == "ielts_toefl":
        examples = IELTS_TOEFL_GRAMMAR_EXAMPLES
    else:
        examples = INTERMEDIATE_GRAMMAR_EXAMPLES
        
    return ExampleStrategy(examples=examples, selection_mode="baseline")


def get_translation_example_strategy(
    plan: GoalExecutionPlan,
) -> ExampleStrategy:
    """获取 translation agent 的 example 策略。"""
    if plan.few_shot_mode != "baseline":
        return ExampleStrategy(examples=[], selection_mode=plan.few_shot_mode)
        
    if plan.goal_id == "academic":
        examples = ACADEMIC_TRANSLATION_EXAMPLES
    elif plan.variant_id == "beginner_reading":
        examples = BEGINNER_TRANSLATION_EXAMPLES
    elif plan.variant_id == "intensive_reading":
        examples = INTENSIVE_TRANSLATION_EXAMPLES
    elif plan.variant_id == "gaokao":
        examples = GAOKAO_TRANSLATION_EXAMPLES
    elif plan.variant_id == "cet":
        examples = CET_TRANSLATION_EXAMPLES
    elif plan.variant_id == "kaoyan":
        examples = KAOYAN_TRANSLATION_EXAMPLES
    elif plan.variant_id == "tem":
        examples = TEM_TRANSLATION_EXAMPLES
    elif plan.variant_id == "ielts_toefl":
        examples = IELTS_TOEFL_TRANSLATION_EXAMPLES
    else:
        examples = INTERMEDIATE_TRANSLATION_EXAMPLES
        
    return ExampleStrategy(examples=examples, selection_mode="baseline")

"""Prompt strategy for V3 workflow.

负责为各 agent 构建 runtime prompt strategy。
设计原则：
- node 不直接拼零散 prompt 片段
- agent 通过统一 strategy builder 获取 prompt 和 examples
- baseline 配置尽量短，尽量少 few-shot
- runtime prompt 采用可替换 section 组装，便于后续 profile 差异化
- 差异化的核心是"用户需要什么"，而非"怎么限制 LLM 输出"
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.planning.goal_views import (
    get_annotation_style,
)
from app.services.analysis.prompting.prompt_composer import PromptSection


@dataclass
class PromptStrategy:
    """Prompt 策略。"""

    profile_id: str
    reading_goal: str
    reading_variant: str
    annotation_style: str | None = None
    translation_style: str | None = None
    grammar_granularity: str | None = None
    vocabulary_policy: str | None = None
    policy_lines: tuple[str, ...] = ()
    extra_instructions: tuple[str, ...] = ()
    extra_sections: tuple[PromptSection, ...] = ()


def build_prompt_sections(strategy: PromptStrategy) -> tuple[PromptSection, ...]:
    """Convert strategy metadata into replaceable runtime sections."""

    profile_lines = [
        f"profile_id: {strategy.profile_id}",
        f"reading_goal: {strategy.reading_goal}",
        f"reading_variant: {strategy.reading_variant}",
    ]
    if strategy.annotation_style:
        profile_lines.append(f"annotation_style: {strategy.annotation_style}")
    if strategy.translation_style:
        profile_lines.append(f"translation_style: {strategy.translation_style}")
    if strategy.grammar_granularity:
        profile_lines.append(f"grammar_granularity: {strategy.grammar_granularity}")
    if strategy.vocabulary_policy:
        profile_lines.append(f"vocabulary_policy: {strategy.vocabulary_policy}")

    sections: list[PromptSection] = [PromptSection("profile", tuple(profile_lines))]
    if strategy.policy_lines:
        sections.append(PromptSection("policy", strategy.policy_lines))
    if strategy.extra_instructions:
        sections.append(
            PromptSection("runtime_constraints", strategy.extra_instructions)
        )
    sections.extend(strategy.extra_sections)
    return tuple(sections)


def build_vocabulary_prompt_strategy(plan: GoalExecutionPlan) -> PromptStrategy:
    """构建 vocabulary agent 的 prompt 策略。"""

    return PromptStrategy(
        profile_id=plan.prompt_profile,
        reading_goal=plan.goal_id,
        reading_variant=plan.variant_id,
        vocabulary_policy=plan.policy.vocabulary_focus,
        annotation_style=get_annotation_style(plan),
        policy_lines=_build_vocabulary_policy_lines(plan),
    )


def build_grammar_prompt_strategy(plan: GoalExecutionPlan) -> PromptStrategy:
    """构建 grammar agent 的 prompt 策略。"""

    return PromptStrategy(
        profile_id=plan.prompt_profile,
        reading_goal=plan.goal_id,
        reading_variant=plan.variant_id,
        grammar_granularity=plan.policy.grammar_focus,
        annotation_style=get_annotation_style(plan),
        policy_lines=_build_grammar_policy_lines(plan),
    )


def build_translation_prompt_strategy(plan: GoalExecutionPlan) -> PromptStrategy:
    """构建 translation agent 的 prompt 策略。"""

    return PromptStrategy(
        profile_id=plan.prompt_profile,
        reading_goal=plan.goal_id,
        reading_variant=plan.variant_id,
        translation_style=plan.policy.translation_focus,
        policy_lines=_build_translation_policy_lines(plan),
    )


def build_repair_prompt_strategy(error_context: str) -> PromptStrategy:
    """构建 repair agent 的 prompt 策略。"""

    return PromptStrategy(
        profile_id="repair",
        reading_goal="repair",
        reading_variant="repair",
        extra_instructions=(error_context,),
    )


def _build_vocabulary_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    focus = plan.policy.vocabulary_focus

    if focus == "high_value_only":
        if plan.variant_id == "beginner_reading":
            return (
                '用户是英语初学者，他们最需要的是：看懂文章 + 学到日常能用的表达。',
                '标词策略：不要标太简单的常见词（如 social, normal, drop, third 等），这些词初学者大概率认识，优先标真正影响理解的词。但释义要直白——直接给中文意思，不要展开词源或辨析。',
                'phrase_gloss 是重点：短语和搭配是初学者最想学的东西。遇到短语动词、日常搭配，优先用 phrase_gloss 标注。',
                '释义中可以给一个简单的日常例句，让用户觉得学完就能用。',
            )
        else:
            return (
                '用户有一定英语基础，他们能读懂大部分内容，但会在多义词的语境义和地道搭配上卡住。',
                '标词策略：只标用户\"认识但可能不确定这里什么意思\"的词和真正地道的搭配。基础词不标。',
                'context_gloss 是重点：多义词在当前语境下的意思，先给语境义，再对比常见义项，解释为什么在这里是这个意思。',
                'phrase_gloss 关注地道搭配和短语动词，释义可以适当举例帮助理解和学习。',
            )
    elif focus == "semantic_nuance":
        return (
            '用户英语水平较高，他们几乎认识所有常见词，但想理解更深层的语义和修辞。',
            '标词策略：只标真正有深度挖掘价值的表达——近义词辨析、搭配隐含义、修辞用法、感情色彩。',
            '释义要有深度：解释作者为什么选这个词而不是近义词，选词的精妙之处在哪里。可以拓展发散，帮助用户建立更丰富的语义网络。',
            '常见词和常见语境义不标。宁缺毋滥。',
        )
    elif focus == "exam_priority":
        if plan.variant_id == "gaokao":
            return (
                '用户是高考备考学生，他们需要掌握考试高频词和固定搭配来提分。',
                '标词策略：优先标高考大纲中的核心词汇，尤其是高中新增词、多义词的常考义项、易混淆词（如 affect/effect, rise/raise）。初中已掌握的基础词不标。',
                'phrase_gloss 是重点：高考完形填空和语法填空大量考固定搭配。遇到短语动词和固定搭配，优先用 phrase_gloss 标注，释义要包含用法提示（如 look forward to + doing sth. 期待做某事）。',
                'context_gloss 用于"词义猜测题"常考的熟词僻义场景，reason 字段要帮用户学会"通过上下文推断词义"的考试策略。',
            )
        if plan.variant_id == "cet":
            return (
                '用户是四六级备考学生，他们需要扩展词汇量和掌握同义替换来提分。',
                '标词策略：优先标四六级新增高频词（超出高考大纲的词），尤其是词性易混淆的同根词（如 economy/economic/economical）、选词填空常考词。高考级别的基础词不标。',
                'phrase_gloss 是最高优先级：四六级阅读的核心考察机制是同义替换，短语搭配是同义替换的主要载体。遇到高频搭配（如 account for, result in, contribute to），优先用 phrase_gloss 标注，释义要包含同义表达提示（如 "account for = 占……比例/解释，同义表达：make up, explain"）。',
                'context_gloss 用于"词义题"和选词填空中需要语境判断的场景，reason 字段可提示"四六级选项常用该词的常见义设置干扰"。',
            )
        return (
            '用户是英语考试备考者，他们需要掌握考试高频词和固定搭配。',
            '标词策略：优先标考试高频词和固定搭配。基础词不标。',
            'phrase_gloss 侧重考试常考搭配，释义包含用法提示。',
        )
    elif focus == "academic_priority":
        return (
            '用户是学术阅读者，他们需要理解专业术语和学术表达。',
            '标词策略：优先标学术术语和专业表达，常见词不标。',
            '释义要准确，可以使用学术领域的标准中文译名。',
        )
    elif focus == "exam_depth":
        if plan.variant_id == "kaoyan":
            return (
                '用户是考研备考学生，词汇量约 5,500 词。他们的核心障碍不是"不认识"，而是"认识但不知道这里什么意思"。',
                '标词策略：优先标熟词僻义（如 address=解决, fashion=方式, issue=发行）和考研高频难词（如 scrutiny, contention, consensus）。CET-4 级别的基础词不标。',
                'phrase_gloss 侧重语篇连接短语和论证性表达（如 in that, by virtue of, on the grounds that），释义要包含短语的逻辑功能说明（如"in that = 因为，用于引出具体原因"）。',
                'context_gloss 是考研词汇考察的核心方式——熟词僻义。reason 应指出常见义为什么在这里不对，可提示"考研常通过熟词僻义考察精确理解"。',
                '重要：只标注文本中确实存在的熟词僻义和考试相关词汇。如果文本较简单、没有值得标注的词，不要硬标。标注质量优先于数量。',
            )
        return (
            '用户是考试备考者，需要掌握熟词僻义和深度词汇辨析。',
            '标词策略：优先标熟词僻义和考试高频难词，常见词不标。',
        )

    return ()


def _build_grammar_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    focus = plan.policy.grammar_focus

    if focus == "explicit_split":
        return (
            '用户是英语初学者，他们不需要系统学语法，但需要看懂长句。你的目标是帮他们拆解句子，同时让他们觉得英语有趣、实用。',
            'sentence_analysis：用于拆解分析长难句，帮用户看清"先看什么、再看什么"。用直白语言，不要用语法术语——说"补充说明"而不是"定语从句"，说"表示原因的部分"而不是"原因状语从句"。',
            'grammar_note 关注实用性：挑出日常能用的表达方式来讲。比如遇到 give up + doing，告诉用户"表示放弃做某事，后面跟动词的 -ing 形式，日常很常用"。让用户觉得学完就能用起来。',
            '可以和中文做对比来帮助理解，比如"英语里这个修饰语放在后面，而中文通常放在前面"。',
        )
    elif focus == "balanced":
        return (
            '用户有一定英语基础，他们能理解大部分句子结构，但会在复杂从句和特殊结构上卡住。',
            'grammar_note 为主：只在结构真正影响理解时才标注。可以适度使用语法术语（如"定语从句""被动语态"），但必须附带直白解释。',
            '讲解策略：先讲清楚结构是什么，再告诉用户这种表达在日常中怎么用。',
            'sentence_analysis 只用于真正复杂的嵌套句，不需要拆解一般从句。',
        )
    elif focus == "structural_logic":
        return (
            '用户英语水平较高，他们能理解大部分句法结构。你的目标是帮他们理解作者为什么选择这种表达方式。',
            '克制标注：只在结构带来修辞效果或隐含逻辑时才分析。简单结构不标。',
            '分析重点：结构如何承载意义——倒装为什么强调、省略为什么紧凑、插入语为什么打断。可使用标准语法术语。',
            'sentence_analysis 用于信息密度极高的句子，分析信息层次和逻辑衔接。',
        )
    elif focus == "explicit_exam":
        if plan.variant_id == "gaokao":
            return (
                '用户是高考备考学生，语法是高考的显性考点。你的目标是帮他们掌握考试常考的语法知识。',
                'grammar_note 采用显性教学：直接命名语法现象（如"定语从句""现在分词作状语"），使用中学英语教学术语。note_zh 要包含三层：① 这是什么语法点 ② 规则是什么 ③ 高考常怎么考。',
                '优先标注高考核心语法点：定语从句、非谓语动词（doing/done/to do）、时态语态、名词性从句。其次是状语从句、强调句、虚拟语气、倒装句。',
                'sentence_analysis 用于帮用户"看清主谓宾"——先说主干（谁做了什么），再说修饰成分，最后可点出考试相关性。使用中学教学术语。',
                '简单句不需要任何标注。但如果句子包含高考常考语法点（如定语从句、非谓语），即使结构不复杂也应标注 grammar_note。',
            )
        return (
            '用户是考试备考者，语法是考试考点。采用显性教学方式讲解语法点。',
        )
    elif focus == "speed_support":
        if plan.variant_id == "cet":
            return (
                '用户是四六级备考学生，语法不是显性考点，但某些结构会拖慢阅读速度。你的目标是帮用户快速识别句子结构，提升阅读速度。',
                'grammar_note 采用"理解提速"方式：指出结构是什么、在句中的作用、快速理解的提示（如"which 从句可先跳过，抓主干"）。不需要深入讲解语法规则。',
                '优先标注拖慢阅读速度的结构：定语从句（影响主干识别）、非谓语动词（压缩信息）、被动语态（动作主体不清）、名词性从句。其次是状语从句、并列结构、同位语、插入语。',
                'sentence_analysis 用于帮用户"快速找到主干信息"——先抽出主干（核心信息），再说明修饰成分各自补充了什么，可点出"在段落匹配题中，这句核心信息可能被改写为……"。',
                '简单句和结构清晰的句子不需要标注。只标注真正影响阅读速度的结构。',
            )
        return (
            '用户需要提升阅读速度，语法标注以理解提速为主。',
        )
    elif focus == "structural":
        if plan.variant_id == "kaoyan":
            return (
                '用户是考研备考学生，长难句是考研英语的核心门槛。你的目标是帮用户拆解复杂句子的层次结构，掌握"找主干、去枝叶、理层次"的拆句方法。',
                'grammar_note 采用"结构分析"方式：说明这个结构在句中起什么作用、修饰/限定的是什么、对理解句意的关键提示。可使用标准语法术语。不需要教语法规则，而是帮用户看清结构。',
                '优先标注考研核心障碍结构：多层从句嵌套（帮用户回到主干）、长距离主谓分离（指出插入语/同位语可先跳过）、复杂并列结构（标出并列边界）、非谓语动词（指出逻辑关系和修饰对象）。其次是强调句、倒装句、虚拟语气、比较结构。',
                'sentence_analysis 是最高优先级——对包含从句嵌套、插入语打断主谓关系、或超过 25 词的复杂句，应提供拆解。先抽出主干，再逐层展开修饰成分，可提示"这种结构在考研翻译题中常见"。chunks 拆到中细粒度。',
                '重要：只标注文本中确实存在的复杂结构。如果文本较简单、句子结构清晰，不需要硬标。简单句不标。标注质量优先于数量，宁缺毋滥。',
            )
        return (
            '用户需要拆解复杂句子结构，语法标注以结构分析为主。',
        )

    return ()


def _build_translation_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    style = plan.policy.translation_focus

    if style == "literal_support":
        if plan.variant_id == "gaokao":
            return (
                '用户是高考备考学生，翻译是他们理解文章和对照学习的重要方式。他们可能会先看翻译，再回看英文。',
                '翻译要忠实详尽，尽量保留原文的逻辑顺序和句子结构，让用户能轻松对照中英文。',
                '必要时可用括号补充原文省略的成分，如"(政府)决定"、"(这)意味着"。',
                '专有名词或术语首次出现时用"中文（英文）"格式，帮助用户积累考试词汇。',
            )
        return (
            '用户是英语初学者，翻译是他们理解文章的主要方式。他们可能会先看翻译，再回看英文。',
            '翻译要忠实详尽，尽量保留原文的逻辑顺序和句子结构，让用户能轻松对照中英文。',
            '必要时可用括号补充原文省略的成分，如"(政府)决定"、"(这)意味着"。',
        )
    elif style == "natural":
        if plan.variant_id == "cet":
            return (
                '用户是四六级备考学生，翻译是他们理解文章和确认理解的重要方式。',
                '翻译追求自然通顺的中文表达，适度体现原文结构，让用户能对照中英文学习。',
                '对含同义替换的关键句，可在翻译后用括号补充提示（如"此处 contribute to 即题目中的 lead to"），帮助用户建立同义替换敏感度。',
                '较长句可适当拆分为短句以提高可读性。',
            )
        return (
            '翻译追求自然通顺的中文表达，不刻意贴英语语序。用户会用翻译来确认自己的理解是否正确。',
        )
    elif style == "nuanced_aesthetic":
        return (
            '用户基本能自主理解原文，翻译的价值在于揭示微妙含义和修辞效果。',
            '在准确传达原文意思的基础上，追求中文表达的文学性和节奏感。对关键词保留英文原文并附注释，帮助读者对照原文品味用词。',
        )
    elif style == "academic":
        if plan.variant_id == "kaoyan":
            return (
                '用户是考研备考学生，翻译既服务于理解，也服务于翻译题备考训练。',
                '翻译要准确，对复杂句应体现清晰的句法映射关系，让用户能对照中英文看清句子结构。',
                '长难句的翻译应保持完整（不拆句），体现原文的层次和逻辑关系。',
                '对特别复杂的句子，可在翻译后用括号补充"此处 XX 指的是…"，帮助用户理解指代关系。',
            )
        return (
            '翻译追求准确和清晰，适度体现原文结构。',
        )

    return ()

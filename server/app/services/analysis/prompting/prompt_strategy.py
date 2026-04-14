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

    return ()


def _build_translation_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    style = plan.policy.translation_focus

    if style == "literal_support":
        return (
            '用户是英语初学者，翻译是他们理解文章的主要方式。他们可能会先看翻译，再回看英文。',
            '翻译要忠实详尽，尽量保留原文的逻辑顺序和句子结构，让用户能轻松对照中英文。',
            '必要时可用括号补充原文省略的成分，如"(政府)决定"、"(这)意味着"。',
        )
    elif style == "natural":
        return (
            '翻译追求自然通顺的中文表达，不刻意贴英语语序。用户会用翻译来确认自己的理解是否正确。',
        )
    elif style == "nuanced_aesthetic":
        return (
            '用户基本能自主理解原文，翻译的价值在于揭示微妙含义和修辞效果。',
            '在准确传达原文意思的基础上，追求中文表达的文学性和节奏感。对关键词保留英文原文并附注释，帮助读者对照原文品味用词。',
        )

    return ()

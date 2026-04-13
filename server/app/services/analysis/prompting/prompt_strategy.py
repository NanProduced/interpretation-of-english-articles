"""Prompt strategy for V3 workflow.

负责为各 agent 构建 runtime prompt strategy。
设计原则：
- node 不直接拼零散 prompt 片段
- agent 通过统一 strategy builder 获取 prompt 和 examples
- baseline 配置尽量短，尽量少 few-shot
- runtime prompt 采用可替换 section 组装，便于后续 profile 差异化
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.planning.goal_views import (
    get_annotation_style,
    get_prompt_baseline_text,
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

    baseline_text = get_prompt_baseline_text(plan)
    extra_instructions = (baseline_text,) if baseline_text else ()

    return PromptStrategy(
        profile_id=plan.prompt_profile,
        reading_goal=plan.goal_id,
        reading_variant=plan.variant_id,
        vocabulary_policy=plan.policy.vocabulary_focus,
        annotation_style=get_annotation_style(plan),
        policy_lines=_build_vocabulary_policy_lines(plan),
        extra_instructions=extra_instructions,
    )


def build_grammar_prompt_strategy(plan: GoalExecutionPlan) -> PromptStrategy:
    """构建 grammar agent 的 prompt 策略。"""

    baseline_text = get_prompt_baseline_text(plan)
    extra_instructions = (baseline_text,) if baseline_text else ()

    return PromptStrategy(
        profile_id=plan.prompt_profile,
        reading_goal=plan.goal_id,
        reading_variant=plan.variant_id,
        grammar_granularity=plan.policy.grammar_focus,
        annotation_style=get_annotation_style(plan),
        policy_lines=_build_grammar_policy_lines(plan),
        extra_instructions=extra_instructions,
    )


def build_translation_prompt_strategy(plan: GoalExecutionPlan) -> PromptStrategy:
    """构建 translation agent 的 prompt 策略。"""

    baseline_text = get_prompt_baseline_text(plan)
    extra_instructions = (baseline_text,) if baseline_text else ()

    return PromptStrategy(
        profile_id=plan.prompt_profile,
        reading_goal=plan.goal_id,
        reading_variant=plan.variant_id,
        translation_style=plan.policy.translation_focus,
        policy_lines=_build_translation_policy_lines(plan),
        extra_instructions=extra_instructions,
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
    lines: list[str] = []
    density = plan.policy.annotation_density
    focus = plan.policy.vocabulary_focus

    lines.append(f"词汇标注上限：每句最多保留 {density} 个高价值词汇点。")

    if focus == "high_value_only":
        if plan.variant_id == "beginner_reading":
            lines.append("选词策略：广覆盖。即使某些词在进阶阅读中算基础词，如果对初学者有门槛也请标注。宁多标也不漏标。")
            lines.append("过滤规则：只过滤 the/is/are 等功能词和极高频日常词。常见基础词如果在该语境下可能不认识，仍然标注。")
        else:
            lines.append("选词策略：精选标注。优先标注多义词的语境义、地道搭配和短语动词。常见基础词、顺着上下文即可读懂的词不标。")
            lines.append("释义要求：先给语境义，再对比常见义项。解释为什么在这里是这个意思而不是平时那个意思。如果是短语可以做一些举例辅助理解或学习。")
            lines.append("过滤规则：用户大概率认识的词不标。宁缺毋滥。")
    elif focus == "semantic_nuance":
        lines.append("选词策略：少标但深挖。只标注近义词辨析、搭配隐含义、修辞用法和感情色彩（褒贬）。")
        lines.append("释义要求：具有启发性和深度。解释作者为什么选这个词而不是近义词，选词的精妙之处在哪里。可以进行拓展发散，帮助用户学习更多相关知识。")
        lines.append("过滤规则：用户大概率认识的词和常见语境义不标。只标真正有深度挖掘价值的表达。")

    return tuple(lines)


def _build_grammar_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    lines: list[str] = []
    focus = plan.policy.grammar_focus

    if focus == "explicit_split":
        lines.append("教学目标：帮用户看懂这句话在说什么，培养语感。")
        lines.append("讲解策略：使用通俗易懂的语言，用户英语水平可能较低，重要的是帮助用户建立英语学习兴趣，可以用和中文做比较来帮助用户理解。")
        lines.append("术语要求：避免语法术语。用'修饰''补充说明''先看...再看...'等直白表达，不要说'定语从句''状语从句'。")
        lines.append("拆解方式：指出句子主干（主语、谓语、宾语），然后说明修饰成分修饰的是谁，按什么顺序读。")
    elif focus == "balanced":
        lines.append("教学目标：帮用户理解结构如何承载意义，以及学会如何去使用这些表达方式。")
        lines.append("讲解策略：先讲清楚语法，再告知日常生活中如何使用。")
        lines.append("术语要求：可适度引入语法术语（如'定语从句''被动语态'），但必须附带直白解释。")
    elif focus == "structural_logic":
        lines.append("教学目标：帮用户理解作者为什么选择这种表达方式。")
        lines.append("讲解策略：克制标注。仅在结构真正阻碍理解或带来修辞效果时才分析。")
        lines.append("术语要求：可使用标准语法术语，用户能理解。")
        lines.append("分析重点：侧重'结构如何承载意义'——倒装为什么强调、省略为什么紧凑、插入语为什么打断。")
        lines.append("触发条件：侧重于高精度的句法解析和语篇逻辑衔接。简单结构不标。")

    return tuple(lines)


def _build_translation_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    lines: list[str] = []
    style = plan.policy.translation_focus

    if style == "literal_support":
        lines.append("翻译角色：翻译是用户的主要理解通道。用户可能先看翻译再回看原文。")
        lines.append("翻译风格：忠实详尽。字面意义与原文尽可能对应，保留原文的逻辑顺序。")
        lines.append("要求：确保初学者能通过翻译快速定位到英文原句的对应成分。")
        lines.append("补充说明：必要时可用括号补充原文省略的主语或逻辑关系，例如：'(政府)决定'、'(这)意味着'。")
    elif style == "natural":
        lines.append("翻译风格：自然意译。追求地道、顺畅的中文表达，不刻意贴英语语序。")
    elif style == "nuanced_aesthetic":
        lines.append("翻译角色：翻译是用户的精细理解辅助。用户基本能自主理解，翻译的价值在于揭示微妙含义和修辞效果。")
        lines.append("翻译风格：优雅且精准。在准确还原逻辑的基础上，尽量体现原文的语气、修辞和文学美感。")
        lines.append("补充说明：对关键表达可附加注释，说明原文此处的隐含义或修辞手法。")

    return tuple(lines)

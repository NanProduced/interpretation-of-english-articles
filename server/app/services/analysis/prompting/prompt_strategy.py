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
    if plan.policy.vocabulary_focus == "high_value_only":
        lines.append(
            f"词汇标注上限：每句最多保留 {plan.policy.annotation_density} 个高价值词汇点。"
        )
        lines.append(
            "优先标注真正影响理解的语境义、固定搭配、短语动词和需要整体解释的表达。"
        )
        lines.append(
            "常见基础词、顺着上下文即可读懂的词、解释价值很低的词不要标。宁缺毋滥。"
        )
    else:
        lines.append(
            f"[Placeholder] Vocabulary focus '{plan.policy.vocabulary_focus}' 策略待细化。"
        )
    return tuple(lines)


def _build_grammar_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    lines: list[str] = []
    if plan.policy.grammar_focus == "balanced":
        lines.append(
            "只处理真正影响理解的结构；普通简单句、常见并列结构、明显直读句不要输出。"
        )
        lines.append(
            "复杂句优先解释主干、从句关系和阅读顺序；局部语法点只在确实妨碍理解时再讲。"
        )
        lines.append("解释保持直白，不追求术语完整性，重点是帮助读者把句子读顺。")
    else:
        lines.append(
            f"[Placeholder] Grammar focus '{plan.policy.grammar_focus}' 策略待细化。"
        )
    return tuple(lines)


def _build_translation_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    lines: list[str] = []
    if plan.policy.translation_focus == "natural":
        lines.append("翻译风格：自然、顺畅、忠实理解，不刻意贴英语语序。")
        lines.append(
            "如果直译影响理解，可按中文表达习惯重组语序，但不要补充原文没有的信息。"
        )
    else:
        lines.append(
            f"[Placeholder] Translation focus '{plan.policy.translation_focus}' 策略待细化。"
        )
    return tuple(lines)

"""Prompt strategy for V3 workflow.

负责为各 agent 构建 prompt 和 strategy bundle。
设计原则：
- node 不直接拼凑零散 prompt 片段
- agent 通过统一的 strategy builder 获取 prompt 和 examples
- 不同 agent 可以接收不同的 strategy 子集
- baseline 配置尽量短，尽量少 few-shot
- 运行时 prompt 以可替换 section 组装，便于后续 profile 差异化
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.internal.execution_plan import GoalExecutionPlan
from app.services.analysis.goal_planner import get_annotation_style, get_prompt_baseline_text
from app.services.analysis.prompt_composer import PromptSection


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

    sections: list[PromptSection] = [
        PromptSection("profile", tuple(profile_lines)),
    ]
    if strategy.policy_lines:
        sections.append(PromptSection("policy", strategy.policy_lines))
    if strategy.extra_instructions:
        sections.append(
            PromptSection("runtime_constraints", strategy.extra_instructions)
        )
    sections.extend(strategy.extra_sections)
    return tuple(sections)


def build_vocabulary_prompt_strategy(
    plan: GoalExecutionPlan,
) -> PromptStrategy:
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


def build_grammar_prompt_strategy(
    plan: GoalExecutionPlan,
) -> PromptStrategy:
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


def build_translation_prompt_strategy(
    plan: GoalExecutionPlan,
) -> PromptStrategy:
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


def build_repair_prompt_strategy(
    error_context: str,
) -> PromptStrategy:
    """构建 repair agent 的 prompt 策略。

    注入错误上下文。
    """
    return PromptStrategy(
        profile_id="repair",
        reading_goal="repair",
        reading_variant="repair",
        extra_instructions=(error_context,),
    )


def _build_vocabulary_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    lines = []
    if plan.policy.vocabulary_focus == "high_value_only":
        lines.append(f"当前标注密度限制：每句平均不超过 {plan.policy.annotation_density} 个词汇点。")
        lines.append("【关键】只标最影响理解、具有解释价值的词汇点（如语境义特殊、短语动词、专业术语）。")
        lines.append("避免标注读者大概率已掌握的基础词汇。宁缺毋滥。")
    else:
        lines.append(f"[Placeholder] Vocabulary focus '{plan.policy.vocabulary_focus}' 策略待细化。")
    return tuple(lines)


def _build_grammar_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    lines = []
    if plan.policy.grammar_focus == "balanced":
        lines.append("在复杂长难句分析与局部语法点（如特殊倒装、强调句）之间保持平衡。")
        lines.append("优先处理可能导致语义理解偏差的结构。")
    else:
        lines.append(f"[Placeholder] Grammar focus '{plan.policy.grammar_focus}' 策略待细化。")
    return tuple(lines)


def _build_translation_policy_lines(plan: GoalExecutionPlan) -> tuple[str, ...]:
    lines = []
    if plan.policy.translation_focus == "natural":
        lines.append("翻译风格：自然意译。优先考虑中文读者的阅读习惯，在不丢失信息的前提下灵活调整语序。")
    else:
        lines.append(f"[Placeholder] Translation focus '{plan.policy.translation_focus}' 策略待细化。")
    return tuple(lines)

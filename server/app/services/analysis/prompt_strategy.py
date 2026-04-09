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

from app.schemas.internal.analysis import UserRules
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


_PROFILE_BASELINES: dict[str, str] = {
    "daily_beginner": "当前 profile=daily_beginner，按 baseline 调试，保持轻量、支持型输出。",
    "daily_intermediate": (
        "当前 profile=daily_intermediate，按 baseline 调试，"
        "不提前模拟 exam 或 academic 风格。"
    ),
    "daily_intensive": (
        "当前 profile=daily_intensive，保持结构化和高信息密度，"
        "但不要越界到考试导向。"
    ),
    "academic_general": "当前 profile=academic_general，允许更正式、更结构化的讲解。",
}


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

    baseline = _PROFILE_BASELINES.get(strategy.profile_id)
    if baseline:
        profile_lines.append(baseline)

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
    user_rules: UserRules,
) -> PromptStrategy:
    """构建 vocabulary agent 的 prompt 策略。

    基线配置：
    - 不额外叠加复杂提示
    - 不额外叠加大量 few-shot
    """
    return PromptStrategy(
        profile_id=user_rules.profile_id,
        reading_goal=user_rules.reading_goal,
        reading_variant=user_rules.reading_variant,
        vocabulary_policy=user_rules.vocabulary_policy,
        annotation_style=user_rules.annotation_style,
        policy_lines=_build_vocabulary_policy_lines(user_rules),
    )


def build_grammar_prompt_strategy(
    user_rules: UserRules,
) -> PromptStrategy:
    """构建 grammar agent 的 prompt 策略。

    基线配置：
    - 不额外叠加复杂提示
    - 保持 grammar_granularity 控制
    """
    return PromptStrategy(
        profile_id=user_rules.profile_id,
        reading_goal=user_rules.reading_goal,
        reading_variant=user_rules.reading_variant,
        grammar_granularity=user_rules.grammar_granularity,
        annotation_style=user_rules.annotation_style,
        policy_lines=_build_grammar_policy_lines(user_rules),
    )


def build_translation_prompt_strategy(
    user_rules: UserRules,
) -> PromptStrategy:
    """构建 translation agent 的 prompt 策略。

    基线配置：
    - 不额外叠加复杂提示
    - 保持 translation_style 控制
    """
    return PromptStrategy(
        profile_id=user_rules.profile_id,
        reading_goal=user_rules.reading_goal,
        reading_variant=user_rules.reading_variant,
        translation_style=user_rules.translation_style,
        policy_lines=_build_translation_policy_lines(user_rules),
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


def _build_vocabulary_policy_lines(user_rules: UserRules) -> tuple[str, ...]:
    lines = []
    if user_rules.vocabulary_policy == "high_value_only":
        lines.append("只标最影响理解的高价值词，宁可漏标，也不要为了覆盖率凑数量。")
    elif user_rules.vocabulary_policy == "exam_priority":
        lines.append("可适度提高考试核心词优先级，但仍要压制低价值噪音。")
    elif user_rules.vocabulary_policy == "academic_priority":
        lines.append("优先保留术语、学术表达和理解门槛明显的词汇点。")
    return tuple(lines)


def _build_grammar_policy_lines(user_rules: UserRules) -> tuple[str, ...]:
    lines = []
    if user_rules.grammar_granularity == "focused":
        lines.append("只标最影响理解的语法点，数量从严。")
    elif user_rules.grammar_granularity == "balanced":
        lines.append("复杂句仍优先，但允许少量高价值局部 grammar_note。")
    elif user_rules.grammar_granularity == "structural":
        lines.append("优先解释句子层次与结构关系，必要时提高 SentenceAnalysis 比重。")
    return tuple(lines)


def _build_translation_policy_lines(user_rules: UserRules) -> tuple[str, ...]:
    lines = []
    if user_rules.translation_style == "natural":
        lines.append("优先自然、通顺、忠实的中文表达。")
    elif user_rules.translation_style == "academic":
        lines.append("保留更正式、更书面的语气，但不要牺牲可读性。")
    elif user_rules.translation_style == "exam":
        lines.append("表达清晰直白，便于学习者看懂句子结构和重点。")
    return tuple(lines)

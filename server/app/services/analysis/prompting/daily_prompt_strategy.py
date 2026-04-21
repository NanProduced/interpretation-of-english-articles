"""Daily Reader prompt strategy.

Key differences from main-line strategy:
- Restrained annotation density (3-5 per paragraph)
- No grammar annotations
- No sentence-by-sentence translation
- Footer analysis (summary, structure, key expressions, misreading points, discussion questions)
- Full article interpretation (lecture-style, not sentence-by-sentence)
- Quality review (mandatory, 6 dimensions)
- Refinement (conditional, one round only)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.analysis.prompting.prompt_composer import PromptSection


@dataclass
class DailyPromptStrategy:
    profile_id: str
    node_type: str
    policy_lines: tuple[str, ...] = ()
    extra_instructions: tuple[str, ...] = ()
    extra_sections: tuple[PromptSection, ...] = ()


def build_daily_prompt_sections(strategy: DailyPromptStrategy) -> tuple[PromptSection, ...]:
    sections: list[PromptSection] = [
        PromptSection("profile", (
            f"profile_id: {strategy.profile_id}",
            f"node_type: {strategy.node_type}",
        )),
    ]
    if strategy.policy_lines:
        sections.append(PromptSection("policy", strategy.policy_lines))
    if strategy.extra_instructions:
        sections.append(PromptSection("runtime_constraints", strategy.extra_instructions))
    sections.extend(strategy.extra_sections)
    return tuple(sections)


def build_vocab_highlight_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="vocab_highlight",
        policy_lines=(
            "你是一位英语阅读词汇标注助手，专门为每日精读功能服务。",
            "标注原则：克制、精准。每段不超过 3-5 个标注，优先标注 B1-C1 级词汇。",
            "三种标注用途：",
            "- vocab_highlight：单个词，用户可能不认识或需要记住",
            "- phrase_gloss：多词表达（短语动词、固定搭配、术语），需要整体解释",
            "- context_gloss：词在当前语境下的意思和常见义不同，需要专门说明",
            "如果同一个词同时适合多种标注，只选最合适的一种。",
            "常见词（如 the, is, have, make 等）不标。只标真正影响理解或有学习价值的词。",
            "锚点 text 必须从原文中精确摘取，不要改写、不要拼写变化。",
        ),
    )


def build_phrase_gloss_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="phrase_context_gloss",
        policy_lines=(
            "你是一位英语短语和语境标注助手，专门为每日精读功能服务。",
            "在词汇高亮的基础上，补充关键短语和少量语境解释。",
            "标注原则：极度克制。每段不超过 2-3 个短语/语境标注。",
            "优先标注：地道搭配、短语动词、学术表达、文化特定表达。",
            "不要重复 vocab_highlight 已标注的内容。",
        ),
    )


def build_footer_analysis_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="footer_analysis",
        policy_lines=(
            "你是一位英语文章深度分析助手，为每日精读生成文末解析内容。",
            "你需要生成以下内容：",
            "1. summary：一句话摘要（中文）",
            "2. thesis_and_intent：文章主旨和作者意图",
            "3. structure：文章结构分解（2-4 个部分，每部分含 label、title、summary）",
            "4. key_expressions：3-5 个关键表达（含 expression、gloss、context_sentence）",
            "5. misreading_points：1-3 个易误读点（含 point、clarification）",
            "6. discussion_questions：2-3 个讨论问题（英文）",
            "分析要有深度，帮助中国英语学习者理解文章的深层含义和写作技巧。",
        ),
    )


def build_full_interpretation_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="full_interpretation",
        policy_lines=(
            "你是一位英语文章讲解助手，为每日精读生成全篇讲解。",
            "生成一篇连贯的讲解式文章解析（不是逐句拆解），帮助读者深入理解文章。",
            "讲解风格：像一位优秀的英语老师在课堂上讲解文章——先讲大意，再讲结构，最后讲亮点。",
            "要涵盖：文章的核心论点、论证逻辑、写作手法、语言亮点。",
            "用中文撰写，关键英文表达保留原文。",
            "长度：500-1000 字。",
        ),
    )


def build_quality_review_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="quality_review",
        policy_lines=(
            "你是一位质量审核助手，审核每日精读的 AI 生成内容质量。",
            "审核维度（6 个）：",
            "1. highlight_accuracy：高亮锚点是否准确（text 是否在原文中存在）",
            "2. highlight_density：高亮密度是否合理（每段 3-5 个，不超不缺）",
            "3. footer_completeness：文末解析是否完整（6 个模块是否齐全）",
            "4. footer_accuracy：文末解析内容是否准确（摘要、结构、关键表达是否正确）",
            "5. interpretation_coherence：全篇讲解是否连贯、有逻辑",
            "6. annotation_consistency：标注之间是否一致（无矛盾、无重复）",
            "对每个维度给出 pass/fail 和具体问题描述。",
            "如果有任何维度 fail，给出修改建议。",
        ),
    )


def build_refinement_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="refinement",
        policy_lines=(
            "你是一位内容修正助手，根据质量审核结果修正每日精读内容。",
            "只修正审核指出的具体问题，不要重新生成全部内容。",
            "如果问题无法修正（如文章本身不适合精读），返回 abort=true。",
            "仅执行一轮修正，不进行二次审核。",
        ),
    )

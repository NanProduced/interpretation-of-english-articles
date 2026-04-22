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
from app.services.analysis.prompting.prompt_loader import load_policy_lines


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
        policy_lines=tuple(load_policy_lines("daily", "vocab_highlight")),
    )


def build_phrase_gloss_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="phrase_context_gloss",
        policy_lines=tuple(load_policy_lines("daily", "phrase_gloss")),
    )


def build_footer_analysis_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="footer_analysis",
        policy_lines=tuple(load_policy_lines("daily", "footer_analysis")),
    )


def build_full_interpretation_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="full_interpretation",
        policy_lines=tuple(load_policy_lines("daily", "full_interpretation")),
    )


def build_quality_review_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="quality_review",
        policy_lines=tuple(load_policy_lines("daily", "quality_review")),
    )


def build_refinement_strategy() -> DailyPromptStrategy:
    return DailyPromptStrategy(
        profile_id="daily_reader",
        node_type="refinement",
        policy_lines=tuple(load_policy_lines("daily", "refinement")),
    )

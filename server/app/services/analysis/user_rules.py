from __future__ import annotations

from app.schemas.internal.analysis import (
    AnnotationBudget,
    ReadingGoal,
    ReadingVariant,
    UserRules,
)


def derive_user_rules(reading_goal: ReadingGoal, reading_variant: ReadingVariant) -> UserRules:
    """把用户配置映射为统一的规则包，供 prompt 与展示层共同消费。"""
    if reading_goal == "exam":
        exam_budget = AnnotationBudget(
            vocabulary_count=6,
            grammar_count=5,
            sentence_note_count=2,
        )
        return UserRules(
            profile_id=f"exam_{reading_variant}",
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            teaching_style="exam_oriented",
            translation_style="exam",
            grammar_granularity="focused",
            vocabulary_policy="exam_priority",
            annotation_budget=exam_budget,
        )

    if reading_goal == "academic":
        academic_budget = AnnotationBudget(
            vocabulary_count=6,
            grammar_count=6,
            sentence_note_count=3,
        )
        return UserRules(
            profile_id="academic_general",
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            teaching_style="structural_and_academic",
            translation_style="academic",
            grammar_granularity="structural",
            vocabulary_policy="academic_priority",
            annotation_budget=academic_budget,
        )

    budget_map = {
        "beginner_reading": AnnotationBudget(
            vocabulary_count=5,
            grammar_count=4,
            sentence_note_count=2,
        ),
        "intermediate_reading": AnnotationBudget(
            vocabulary_count=6,
            grammar_count=5,
            sentence_note_count=2,
        ),
        "intensive_reading": AnnotationBudget(
            vocabulary_count=7,
            grammar_count=6,
            sentence_note_count=3,
        ),
    }
    return UserRules(
        profile_id=f"daily_{reading_variant.removesuffix('_reading')}",
        reading_goal=reading_goal,
        reading_variant=reading_variant,
        teaching_style="plain_and_supportive",
        translation_style="natural",
        grammar_granularity="focused" if reading_variant == "beginner_reading" else "balanced",
        vocabulary_policy="high_value_only",
        annotation_budget=budget_map[reading_variant],
    )

from __future__ import annotations

from app.schemas.internal.analysis import ReadingGoal, ReadingVariant, UserRules


def derive_user_rules(reading_goal: ReadingGoal, reading_variant: ReadingVariant) -> UserRules:
    """把请求场景映射为轻量规则包，供 prompt 与展示层消费。"""
    if reading_goal == "exam":
        if reading_variant == "gre":
            return UserRules(
                profile_id="exam_gre",
                reading_goal=reading_goal,
                reading_variant=reading_variant,
                annotation_style="structural_and_academic",
                translation_style="academic",
                grammar_granularity="structural",
                vocabulary_policy="academic_priority",
            )
        if reading_variant == "ielts_toefl":
            return UserRules(
                profile_id="exam_ielts_toefl",
                reading_goal=reading_goal,
                reading_variant=reading_variant,
                annotation_style="exam_oriented",
                translation_style="natural",
                grammar_granularity="balanced",
                vocabulary_policy="exam_priority",
            )
        return UserRules(
            profile_id=f"exam_{reading_variant}",
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            annotation_style="exam_oriented",
            translation_style="exam",
            grammar_granularity="focused",
            vocabulary_policy="exam_priority",
        )

    if reading_goal == "academic":
        return UserRules(
            profile_id="academic_general",
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            annotation_style="structural_and_academic",
            translation_style="academic",
            grammar_granularity="structural",
            vocabulary_policy="academic_priority",
        )

    variant_map: dict[str, tuple[str, str, str]] = {
        "beginner_reading": ("daily_beginner", "focused", "high_value_only"),
        "intermediate_reading": ("daily_intermediate", "balanced", "high_value_only"),
        "intensive_reading": ("daily_intensive", "structural", "academic_priority"),
    }
    profile_id, grammar_granularity, vocabulary_policy = variant_map[reading_variant]
    return UserRules(
        profile_id=profile_id,
        reading_goal=reading_goal,
        reading_variant=reading_variant,
        annotation_style="plain_and_supportive",
        translation_style="natural",
        grammar_granularity=grammar_granularity,
        vocabulary_policy=vocabulary_policy,
    )

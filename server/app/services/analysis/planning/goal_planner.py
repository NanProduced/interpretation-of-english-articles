from __future__ import annotations

from app.schemas.internal.analysis import ReadingGoal, ReadingVariant
from app.schemas.internal.execution_plan import GoalExecutionPlan, GoalPolicy


def build_goal_execution_plan(reading_goal: ReadingGoal, reading_variant: ReadingVariant) -> GoalExecutionPlan:
    """把请求场景映射为包含拓扑策略和密度策略的 ExecutionPlan。"""
    
    if reading_goal == "exam":
        if reading_variant == "gre_tem":
            policy = GoalPolicy(
                annotation_density=4,
                vocabulary_focus="academic_priority",
                grammar_focus="structural",
                translation_focus="academic",
            )
            return GoalExecutionPlan(
                goal_id=reading_goal,
                variant_id=reading_variant,
                topology_mode="learning",
                output_mode="learning_scene",
                prompt_profile="exam_gre_tem",
                policy=policy,
            )
        if reading_variant == "ielts_toefl":
            policy = GoalPolicy(
                annotation_density=4,
                vocabulary_focus="exam_priority",
                grammar_focus="balanced",
                translation_focus="natural",
            )
            return GoalExecutionPlan(
                goal_id=reading_goal,
                variant_id=reading_variant,
                topology_mode="learning",
                output_mode="learning_scene",
                prompt_profile="exam_ielts_toefl",
                policy=policy,
            )
        
        policy = GoalPolicy(
            annotation_density=4,
            vocabulary_focus="exam_priority",
            grammar_focus="focused",
            translation_focus="exam",
        )
        return GoalExecutionPlan(
            goal_id=reading_goal,
            variant_id=reading_variant,
            topology_mode="learning",
            output_mode="learning_scene",
            prompt_profile=f"exam_{reading_variant}",
            policy=policy,
        )

    if reading_goal == "academic":
        policy = GoalPolicy(
            annotation_density=4,
            vocabulary_focus="academic_priority",
            grammar_focus="structural",
            translation_focus="academic",
        )
        return GoalExecutionPlan(
            goal_id=reading_goal,
            variant_id=reading_variant,
            topology_mode="academic", # 分开建模，不再假装是 learning
            output_mode="academic_scene",
            prompt_profile="academic_general",
            policy=policy,
        )

    variant_map: dict[str, tuple[str, str, str, int]] = {
        "beginner_reading": ("daily_beginner", "focused", "high_value_only", 2),
        "intermediate_reading": ("daily_intermediate", "balanced", "high_value_only", 3),
        "intensive_reading": ("daily_intensive", "structural", "academic_priority", 4),
    }
    profile_id, grammar_granularity, vocabulary_policy, density = variant_map[reading_variant]
    
    policy = GoalPolicy(
        annotation_density=density,
        vocabulary_focus=vocabulary_policy,
        grammar_focus=grammar_granularity,
        translation_focus="natural",
    )
    return GoalExecutionPlan(
        goal_id=reading_goal,
        variant_id=reading_variant,
        topology_mode="learning",
        output_mode="learning_scene",
        prompt_profile=profile_id,
        policy=policy,
    )

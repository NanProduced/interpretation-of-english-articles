from __future__ import annotations

from app.schemas.internal.analysis import ReadingGoal, ReadingVariant
from app.schemas.internal.execution_plan import GoalExecutionPlan, GoalPolicy


_PROFILE_BASELINES: dict[str, str] = {
    "daily_beginner": "[Placeholder] 日常基础模式风格待定。",
    "daily_intermediate": (
        "当前 profile=daily_intermediate，按 baseline 调试。"
        "目标：为具有一定基础的阅读者提供辅助。不追求考点覆盖，而是追求‘清除阅读卡顿’。"
        "要求：标注应聚焦于语境难词和中等复杂的句法结构，翻译保持自然意译。"
    ),
    "daily_intensive": "[Placeholder] 日常精读模式风格待定。",
    "academic_general": "[Placeholder] 学术通用模式风格待定。",
    "exam_gre_tem": "[Placeholder] 考研/专四专八模式风格待定。",
    "exam_ielts_toefl": "[Placeholder] 雅思/托福模式风格待定。",
}


def build_goal_execution_plan(reading_goal: ReadingGoal, reading_variant: ReadingVariant) -> GoalExecutionPlan:
    """把请求场景映射为包含拓扑策略和密度策略的 ExecutionPlan。"""
    
    if reading_goal == "exam":
        if reading_variant in ("gre", "gre_tem"):
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
                output_mode="learning_scene_v1",
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
                output_mode="learning_scene_v1",
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
            output_mode="learning_scene_v1",
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
            output_mode="academic_scene_v1",
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
        output_mode="learning_scene_v1",
        prompt_profile=profile_id,
        policy=policy,
    )


def get_annotation_style(plan: GoalExecutionPlan) -> str:
    """根据执行计划获取标注风格描述。"""
    if plan.goal_id == "exam":
        return "structural_and_academic" if plan.variant_id in ("gre", "gre_tem") else "exam_oriented"
    elif plan.goal_id == "academic":
        return "structural_and_academic"
    return "plain_and_supportive"


def get_prompt_baseline_text(plan: GoalExecutionPlan) -> str | None:
    """获取 Prompt 中的基线调试文本。"""
    return _PROFILE_BASELINES.get(plan.prompt_profile)

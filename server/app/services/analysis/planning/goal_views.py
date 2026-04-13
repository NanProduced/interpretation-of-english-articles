from __future__ import annotations

from app.schemas.internal.execution_plan import GoalExecutionPlan

_PROFILE_BASELINES: dict[str, str] = {
    "daily_beginner": "[Placeholder] 日常基础模式风格待定。",
    "daily_intermediate": (
        "本次任务是基础阅读辅助，不做考试解析，也不做学术导读。"
        "目标是帮助具有一定基础的读者减少阅读卡顿，优先解决真正影响理解的词、短语和句子结构。"
        "说明保持直白、克制、易懂；能直接读懂的内容不要硬标。"
    ),
    "daily_intensive": "[Placeholder] 日常精读模式风格待定。",
    "academic_general": "[Placeholder] 学术通用模式风格待定。",
    "exam_gre_tem": "[Placeholder] 考研/专四专八模式风格待定。",
    "exam_ielts_toefl": "[Placeholder] 雅思/托福模式风格待定。",
}


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

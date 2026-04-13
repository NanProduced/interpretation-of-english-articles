from __future__ import annotations

from app.schemas.internal.execution_plan import GoalExecutionPlan

_PROFILE_BASELINES: dict[str, str] = {
    "daily_beginner": (
        "用户是英语初学者，词汇量约 1,500\u20133,000 词。"
        "他们读英语文章时，很多词不认识，长句看不懂结构。"
        "他们学英语不是为了考试，而是想在日常生活中用起来。"
        "所以：帮他们看懂文章在说什么，同时让他们学到日常能用的表达。"
    ),
    "daily_intermediate": (
        "用户有一定英语基础，词汇量约 3,000\u20135,000 词。"
        "他们能读懂大部分内容，但会在多义词语境义和复杂结构上卡住。"
        "他们想确认自己的理解是否正确，顺便学到一些地道表达。"
    ),
    "daily_intensive": (
        "用户英语水平较高，词汇量约 5,000\u20138,000 词。"
        "他们几乎能自主理解全文，但想更深入地理解作者的用词选择和表达技巧。"
    ),
    "academic_general": "[Placeholder] 学术通用模式风格待定。",
    "exam_kaoyan": "[Placeholder] 考研英语模式风格待定。",
    "exam_tem": "[Placeholder] 专业英语模式风格待定。",
    "exam_ielts_toefl": "[Placeholder] 雅思/托福模式风格待定。",
}


def get_annotation_style(plan: GoalExecutionPlan) -> str:
    if plan.goal_id == "exam":
        return "structural_and_academic" if plan.variant_id in ("kaoyan", "tem") else "exam_oriented"
    elif plan.goal_id == "academic":
        return "structural_and_academic"
    return "plain_and_supportive"


def get_prompt_baseline_text(plan: GoalExecutionPlan) -> str | None:
    return _PROFILE_BASELINES.get(plan.prompt_profile)

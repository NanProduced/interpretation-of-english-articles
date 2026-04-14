from __future__ import annotations

from app.schemas.internal.execution_plan import GoalExecutionPlan

_PROFILE_BASELINES: dict[str, str] = {
    "daily_beginner": (
        "用户是英语初学者，词汇量约 1,500–3,000 词。"
        "他们读英语文章时，很多词不认识，长句看不懂结构。"
        "他们学英语不是为了考试，而是想在日常生活中用起来。"
        "所以：帮助他们建立语感，让他们看懂文章在说什么，同时让他们学到日常能用的表达。"
    ),
    "daily_intermediate": (
        "用户有一定英语基础，词汇量约 3,000–5,000 词。"
        "他们能读懂大部分内容，但会在多义词语境义和复杂结构上卡住。"
        "他们想确认自己的理解是否正确，顺便学到一些地道表达，提升自己的语感。"
    ),
    "daily_intensive": (
        "用户英语水平较高，词汇量约 5,000–8,000 词。"
        "他们几乎能自主理解全文，但想更深入地理解作者的用词选择和表达技巧。主要是想在日常阅读里提升自己的英语能力。"
    ),
    "academic_general": "[Placeholder] 学术通用模式风格待定。",
    "exam_gaokao": (
        "用户是高考英语备考学生，词汇量约 3,500 词（高中大纲）。"
        "他们读英语文章时，大部分词认识，但会在多义词语境义和复杂句结构上卡住。"
        "他们学英语的核心目标是考试提分，所以需要：看懂文章 + 掌握考试常考的语言知识点。"
        "语法是高考的显性考点，需要直接告诉他们'这是什么语法点、规则是什么、考试怎么考'。"
        "词汇标注应侧重考试高频词和固定搭配，释义要包含用法提示（如 to 后接 doing 还是 do）。"
    ),
    "exam_tem": "[Placeholder] 专业英语模式风格待定。",
    "exam_ielts_toefl": "[Placeholder] 雅思/托福模式风格待定。",
}


def get_annotation_style(plan: GoalExecutionPlan) -> str:
    if plan.goal_id == "exam":
        if plan.variant_id == "gaokao":
            return "exam_gaokao"
        return "structural_and_academic" if plan.variant_id in ("kaoyan", "tem") else "exam_oriented"
    elif plan.goal_id == "academic":
        return "structural_and_academic"
    return "plain_and_supportive"


def get_prompt_baseline_text(plan: GoalExecutionPlan) -> str | None:
    return _PROFILE_BASELINES.get(plan.prompt_profile)

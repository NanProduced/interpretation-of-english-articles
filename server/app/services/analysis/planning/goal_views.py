from __future__ import annotations

from app.schemas.internal.execution_plan import GoalExecutionPlan

_PROFILE_BASELINES: dict[str, str] = {
    "daily_beginner": (
        "本次任务是入门级阅读辅助，用户英语水平约 CEFR A2–B1，词汇量约 1,500–3,000 词族。"
        "用户严重依赖自下而上处理和翻译辅助，可能先看翻译再回看原文。"
        "核心目标：帮用户看懂这篇文章在说什么。"
        "策略总方向：广覆盖、浅解释——多标词但解释要直白，积极拆句但避免语法术语，翻译忠实原文结构确保中英对照清晰。"
    ),
    "daily_intermediate": (
        "本次任务是中阶阅读辅助，用户英语水平约 CEFR B1–B2，词汇量约 3,000–5,000 词族。"
        "核心目标：帮用户确认理解对不对，顺便学到一些东西。"
        "策略总方向：精选标注、语境义优先——不标用户大概率认识的词，聚焦'认识但这里不确定'的情况；语法只在影响理解时点出；翻译自然通顺即可。"
    ),
    "daily_intensive": (
        "本次任务是深度精读辅助，用户英语水平约 CEFR B2–C1，词汇量约 5,000–8,000 词族。"
        "核心目标：帮用户更深入地理解这篇文章的细节和表达。"
        "策略总方向：少标但深挖——聚焦近义词辨析、搭配隐含义和修辞用法，语法侧重'为什么这样写'而非'这是什么结构'，翻译在准确基础上体现原文韵味。"
    ),
    "academic_general": "[Placeholder] 学术通用模式风格待定。",
    "exam_kaoyan": "[Placeholder] 考研英语模式风格待定。",
    "exam_tem": "[Placeholder] 专业英语模式风格待定。",
    "exam_ielts_toefl": "[Placeholder] 雅思/托福模式风格待定。",
}


def get_annotation_style(plan: GoalExecutionPlan) -> str:
    """根据执行计划获取标注风格描述。"""
    if plan.goal_id == "exam":
        return "structural_and_academic" if plan.variant_id in ("kaoyan", "tem") else "exam_oriented"
    elif plan.goal_id == "academic":
        return "structural_and_academic"
    return "plain_and_supportive"


def get_prompt_baseline_text(plan: GoalExecutionPlan) -> str | None:
    """获取 Prompt 中的基线调试文本。"""
    return _PROFILE_BASELINES.get(plan.prompt_profile)

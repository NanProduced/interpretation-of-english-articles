from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.internal.analysis import (
    GrammarGranularity,
    ReadingGoal,
    ReadingVariant,
    TranslationStyle,
    VocabularyPolicy,
)


class GoalPolicy(BaseModel):
    """确定性硬策略，供 normalize 阶段消费。"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    annotation_density: int = Field(ge=1, description="控制每句最大标注数。")
    vocabulary_focus: VocabularyPolicy = Field(description="词汇筛选策略。")
    grammar_focus: GrammarGranularity = Field(description="语法侧重点。")
    translation_focus: TranslationStyle = Field(description="翻译侧重点。")


class GoalExecutionPlan(BaseModel):
    """请求场景的整体执行计划。"""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    goal_id: ReadingGoal = Field(description="阅读目标。")
    variant_id: ReadingVariant = Field(description="阅读变体。")
    topology_mode: Literal["learning", "academic"] = Field(description="工作流拓扑模式。")
    output_mode: Literal["learning_scene", "academic_scene"] = Field(description="输出渲染模式。")
    prompt_profile: str = Field(description="对应旧的 profile_id。")
    few_shot_mode: Literal["baseline", "manual", "rag"] = Field(default="baseline", description="Few-shot 策略。")
    policy: GoalPolicy = Field(description="后处理硬策略。")

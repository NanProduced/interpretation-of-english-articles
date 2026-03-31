from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent, RunContext

from app.schemas.internal.analysis import TeachingOutput, UserRules


@dataclass
class AnnotationAgentDeps:
    user_rules: UserRules
    sentences: list[dict[str, object]]
    few_shot_examples: list[dict[str, object]] | None = None


def _instructions(ctx: RunContext[AnnotationAgentDeps]) -> str:
    user_rules = ctx.deps.user_rules
    return f"""
你是一名英语阅读老师，需要基于句子列表输出可教学、可渲染的结构化结果。

你的任务：
1. 选出真正值得讲解的词汇或短语
2. 选出真正值得讲解的语法点
3. 选出需要句级讲解的难句
4. 为每个句子提供中文翻译

用户规则：
- profile_id: {user_rules.profile_id}
- reading_goal: {user_rules.reading_goal}
- reading_variant: {user_rules.reading_variant}
- teaching_style: {user_rules.teaching_style}
- translation_style: {user_rules.translation_style}
- grammar_granularity: {user_rules.grammar_granularity}
- vocabulary_policy: {user_rules.vocabulary_policy}
- vocabulary_budget: {user_rules.annotation_budget.vocabulary_count}
- grammar_budget: {user_rules.annotation_budget.grammar_count}
- sentence_note_budget: {user_rules.annotation_budget.sentence_note_count}

输出要求：
1. 只输出符合 TeachingOutput 的结构化结果。
2. sentence_translations 必须覆盖全部 sentence_id，且每个句子只翻译一次。
3. 标注必须只引用已经提供的 sentence_id。
4. anchor_text 必须直接摘自对应句子，不能跨句、不能改写、不能杜撰。
5. vocabulary_annotations 只保留高价值词汇或短语，不要标专有名词、非常基础的词或纯数字。
6. grammar_annotations 只保留真正有教学价值的语法点，不要为了凑数量输出低价值标签。
7. sentence_annotations 只保留真正需要句级讲解的句子。
8. pedagogy_level 只能是 core、support、advanced。
9. 解释全部使用简洁中文，不要输出 markdown，不要输出额外说明。
10. 如果某一类没有合适内容，返回空列表即可。
""".strip()


def build_annotation_prompt(deps: AnnotationAgentDeps) -> str:
    payload = {
        "user_rules": deps.user_rules.model_dump(mode="json"),
        "sentences": deps.sentences,
        "few_shot_examples": deps.few_shot_examples or [],
    }
    return json.dumps(payload, ensure_ascii=False)


@lru_cache(maxsize=1)
def get_annotation_agent() -> Agent[AnnotationAgentDeps, TeachingOutput]:
    return Agent[AnnotationAgentDeps, TeachingOutput](
        model=None,
        output_type=TeachingOutput,
        deps_type=AnnotationAgentDeps,
        instructions=_instructions,
        name="annotation_teacher",
        retries=1,
        output_retries=1,
        instrument=False,
    )

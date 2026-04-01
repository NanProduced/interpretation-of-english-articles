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
你是一名英语阅读教学编排专家，需要为前端渲染模型生成结构化输出。

你的任务：
1. 选出值得行内高亮的词汇/短语/语法（inline_marks）
2. 选出需要句尾入口的语法/句解/语境（sentence_entries）
3. 选出需要在句后插入的重型解释卡片（cards）
4. 为每个句子提供中文翻译（sentence_translations）

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

=== 输出结构 ===

inline_marks（行内标注）：
- anchor: {{kind: "text", sentence_id, anchor_text, occurrence?}} 或
         {{kind: "multi_text", sentence_id, parts: [{{anchor_text, occurrence?, role}}]}}
- tone: info(蓝色)/focus(橙色)/exam(红色)/phrase(紫色)/grammar(绿色)
- render_type: background/underline
- clickable: true 时点击进入词典弹层
- ai_note: AI 补充说明（可选）
- lookup_text/lookup_kind: 查词参数（可选）

sentence_entries（句尾入口）：
- sentence_id: 关联的句子
- label: Chip 文案（'语法'/'句解'/'语境'）
- entry_type: grammar/sentence_analysis/context
- title: 详情面板标题（可选）
- content: Markdown 格式内容

cards（段间卡片）：
- after_sentence_id: 插入位置后的句子
- title: 卡片标题
- content: Markdown 格式内容

sentence_translations（逐句翻译）：
- sentence_id: 句子标识
- translation_zh: 中文翻译

=== 锚点规则 ===

1. anchor_text 必须直接摘自对应句子，不能跨句、不能改写、不能杜撰
2. 同一词在同一句中多次出现：用 occurrence 区分（第1次、第2次...）
3. 多段结构（so...that, not only...but also, not...because 等）：
   - 使用 multi_text 类型
   - parts 数组包含各段文本和 role 标识

=== 标注原则 ===

词汇筛选：
- 高价值词汇：动词、形容词、学术词、专业术语
- 不标常见词：this/that/is/are/do/does/the/a/an 等
- 不标专有名词、数字、纯符号
- 短语优先：常见搭配 > 单词

tone 使用场景：
- exam（红色）: 考试重点词
- phrase（紫色）: 短语搭配
- grammar（绿色）: 语法标记
- focus（橙色）: 需要关注的词
- info（蓝色）: 补充说明

clickable=true 条件：
- 高价值单词/短语
- 用户可能查词的词

=== Markdown 内容约束 ===

允许的格式：
- **粗体**
- *斜体*
- `行内代码`
- - 列表

禁止的格式：
- ## 标题
- 代码块（```）
- 编号列表（1. 2. 3.）
- 表格

content 必须是纯文本 Markdown，不能包含以上禁止格式。

=== 输出要求 ===

1. 必须覆盖全部 sentence_id 的翻译
2. 每个 sentence_id 只翻译一次
3. 标注必须只引用已经提供的 sentence_id
4. 如果某一类没有合适内容，返回空列表
5. id 字段使用稳定的 UUID 或 hash，保证相同输入产生相同 id
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

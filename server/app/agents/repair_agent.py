"""Repair agent for V3 workflow.

在 normalize_and_ground 失败时触发。
职责：修复结构性问题，不新增语义标注。

可修复范围：
- sentence_id
- anchor_text
- 补齐缺失字段
- 修正枚举值与结构格式
- 删除无效项

不可做的事：
- 凭空新增新的语义标注点
- 改写原有标注意图
- 重做全文分析
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_ai import Agent

from app.schemas.internal.normalized import NormalizedAnnotationResult


@dataclass
class RepairAgentDeps:
    """Repair agent 依赖。"""
    sentences: list[dict[str, object]]
    original_drafts: dict[str, object]  # 原始 drafts 引用，用于修复时参考


REPAIR_INSTRUCTIONS = """
你是修复代理，专门修复结构性问题。

触发条件：normalize_and_ground 阶段失败（parse 失败、grounding 失败率过高、关键组件整类缺失等）。

任务：在不改变原有标注意图的前提下，修复结构性问题。

【可修复范围】
1. sentence_id 错误
2. anchor_text 不在对应句子中
3. 缺失字段（exam_tags、phrase_type 等）
4. 枚举值错误
5. 结构格式错误
6. 删除无法 grounding 的无效项

【不可做的事】
1. 不要凭空新增新的语义标注点。
2. 不要改写原有标注意图。
3. 不要重做全文分析。

【修复原则】
1. 最小化修改，只修复必要的结构问题。
2. 优先修复，不轻易删除；如果必须删除，记录原因。
3. 修复后输出仍必须符合 schema 规范。

【输出要求】
1. 返回修复后的 NormalizedAnnotationResult。
2. 如有删除项，必须记录 drop_reason。
3. 如有修改项，必须记录 repair_reason。
""".strip()


def build_repair_prompt(
    deps: RepairAgentDeps,
    error_context: str,
) -> str:
    import json

    sentence_lines = [
        f"{sentence['sentence_id']}: {sentence['text']}"
        for sentence in deps.sentences
    ]

    # 包含原始 drafts 供修复参考
    vocab_draft_str = json.dumps(
        deps.original_drafts.get("vocabulary_draft", {}), ensure_ascii=False, indent=2
    )
    grammar_draft_str = json.dumps(
        deps.original_drafts.get("grammar_draft", {}), ensure_ascii=False, indent=2
    )
    translation_draft_str = json.dumps(
        deps.original_drafts.get("translation_draft", {}), ensure_ascii=False, indent=2
    )

    return "\n".join(
        [
            "句子列表：",
            *sentence_lines,
            "",
            "错误上下文：",
            error_context,
            "",
            "原始 Vocabulary Draft：",
            vocab_draft_str,
            "",
            "原始 Grammar Draft：",
            grammar_draft_str,
            "",
            "原始 Translation Draft：",
            translation_draft_str,
        ]
    )


@lru_cache(maxsize=1)
def get_repair_agent() -> Agent[RepairAgentDeps, NormalizedAnnotationResult]:
    return Agent[RepairAgentDeps, NormalizedAnnotationResult](
        model=None,
        output_type=NormalizedAnnotationResult,
        deps_type=RepairAgentDeps,
        instructions=REPAIR_INSTRUCTIONS,
        name="repair_agent",
        retries=1,
        output_retries=1,
        instrument=False,
    )

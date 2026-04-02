"""Normalize and ground for V3 workflow.

这是 V3 最关键的稳定化节点。
不是简单 validator，而是"候选结果收敛层"。

职责：
1. 合并 vocabulary_draft、grammar_draft、translation_draft
2. 做 substring grounding 校验
3. 校验 sentence_id
4. 处理 occurrence
5. 去重
6. 同句密度控制
7. 低价值标注裁剪
8. 类型冲突消解
9. 缺失字段清理
10. 生成删除/降级日志

设计原则：
- 删除 annotation 必须记录日志
- 冲突优先级：context_gloss > phrase_gloss > vocab_highlight
- grammar_note 与词汇类不互斥
- sentence_analysis 独立存在
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.schemas.internal.analysis import (
    Annotation,
    ContextGloss,
    GrammarNote,
    PhraseGloss,
    PreparedSentence,
    SentenceAnalysis,
    SentenceTranslation,
    VocabHighlight,
)
from app.schemas.internal.drafts import GrammarDraft, TranslationDraft, VocabularyDraft
from app.schemas.internal.normalized import DropLogEntry, NormalizedAnnotationResult
from app.services.analysis.draft_validators import validate_all_drafts

# 冲突优先级：context_gloss > phrase_gloss > vocab_highlight
PRIORITY_RANK: dict[str, int] = {
    "context_gloss": 3,
    "phrase_gloss": 2,
    "vocab_highlight": 1,
    "grammar_note": 10,  # 与词汇类不互斥，优先级独立
    "sentence_analysis": 10,  # 独立存在
}

# 低价值词列表（不进入 vocab_highlight）
LOW_VALUE_WORDS: set[str] = {
    "this", "that", "these", "those", "the", "a", "an",
    "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must",
    "shall", "can", "need", "dare", "ought", "used",
    "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before",
    "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very",
    "just", "but", "and", "or", "if", "because", "until",
    "while", "review", "series", "site", "item", "case",
    "page", "form", "part", "point", "way", "time",
    "year", "week", "day", "hour", "minute", "second",
    "number", "percent", "type", "kind", "sort", "class",
}


@dataclass
class NormalizationContext:
    """归一化上下文。"""
    sentences: list[PreparedSentence]
    sentence_map: dict[str, PreparedSentence]


def _make_anchor_key(
    annotation_type: str,
    sentence_id: str,
    anchor_text: str,
) -> str:
    """生成标注的唯一锚点 key。"""
    canonical = json.dumps(
        {"type": annotation_type, "sentence_id": sentence_id, "text": anchor_text},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]
    return f"{annotation_type}_{sentence_id}_{digest}"


def _is_substring(text: str, sentence_text: str) -> bool:
    """检查 text 是否为 sentence_text 的子串。"""
    return text in sentence_text


def _log_drop(
    source_agent: Literal["vocabulary", "grammar", "translation"],
    annotation_type: str,
    sentence_id: str,
    anchor_text: str,
    drop_reason: str,
    drop_stage: Literal["grounding", "deduplication", "conflict_resolution", "density_control", "pruning"],
    drop_log: list[DropLogEntry],
) -> None:
    """记录删除日志。"""
    drop_log.append(
        DropLogEntry(
            source_agent=source_agent,
            annotation_type=annotation_type,
            sentence_id=sentence_id,
            anchor_text=anchor_text,
            drop_reason=drop_reason,
            drop_stage=drop_stage,
            dropped_at=datetime.now(),
        )
    )


def _grounding_check(
    annotation_type: str,
    text: str,
    sentence_id: str,
    sentence_map: dict[str, PreparedSentence],
    source_agent: Literal["vocabulary", "grammar", "translation"],
    drop_log: list[DropLogEntry],
) -> bool:
    """检查锚点是否在句子中。返回 True 表示通过，False 表示失败并已记录日志。"""
    sentence_obj = sentence_map.get(sentence_id)
    if sentence_obj is None:
        _log_drop(
            source_agent, annotation_type, sentence_id, text,
            "sentence_id_not_found", "grounding", drop_log
        )
        return False
    if not _is_substring(text, sentence_obj.text):
        _log_drop(
            source_agent, annotation_type, sentence_id, text,
            "anchor_not_substring", "grounding", drop_log
        )
        return False
    return True


def _check_low_value_word(text: str) -> bool:
    """检查是否为低价值词。"""
    return text.lower() in LOW_VALUE_WORDS


def _normalize_vocab_highlights(
    draft: VocabularyDraft,
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
) -> list[VocabHighlight]:
    """归一化 vocab_highlights。"""
    result: list[VocabHighlight] = []
    seen_keys: set[str] = set()

    for v in draft.vocab_highlights:
        # Grounding 检查
        if not _grounding_check("vocab_highlight", v.text, v.sentence_id, ctx.sentence_map, "vocabulary", drop_log):
            continue

        # 低价值词过滤
        if _check_low_value_word(v.text):
            _log_drop(
                "vocabulary", "vocab_highlight", v.sentence_id, v.text,
                "low_value_word", "pruning", drop_log
            )
            continue

        # 去重
        key = _make_anchor_key("vocab_highlight", v.sentence_id, v.text)
        if key in seen_keys:
            _log_drop(
                "vocabulary", "vocab_highlight", v.sentence_id, v.text,
                "duplicate", "deduplication", drop_log
            )
            continue
        seen_keys.add(key)
        result.append(v)

    return result


def _normalize_phrase_glosses(
    draft: VocabularyDraft,
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
) -> list[PhraseGloss]:
    """归一化 phrase_glosses。"""
    result: list[PhraseGloss] = []
    seen_keys: set[str] = set()

    for p in draft.phrase_glosses:
        # Grounding 检查
        if not _grounding_check("phrase_gloss", p.text, p.sentence_id, ctx.sentence_map, "vocabulary", drop_log):
            continue

        # 去重
        key = _make_anchor_key("phrase_gloss", p.sentence_id, p.text)
        if key in seen_keys:
            _log_drop(
                "vocabulary", "phrase_gloss", p.sentence_id, p.text,
                "duplicate", "deduplication", drop_log
            )
            continue
        seen_keys.add(key)
        result.append(p)

    return result


def _normalize_context_glosses(
    draft: VocabularyDraft,
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
) -> list[ContextGloss]:
    """归一化 context_glosses。"""
    result: list[ContextGloss] = []
    seen_keys: set[str] = set()

    for c in draft.context_glosses:
        # Grounding 检查
        if not _grounding_check("context_gloss", c.text, c.sentence_id, ctx.sentence_map, "vocabulary", drop_log):
            continue

        # 去重
        key = _make_anchor_key("context_gloss", c.sentence_id, c.text)
        if key in seen_keys:
            _log_drop(
                "vocabulary", "context_gloss", c.sentence_id, c.text,
                "duplicate", "deduplication", drop_log
            )
            continue
        seen_keys.add(key)
        result.append(c)

    return result


def _normalize_grammar_notes(
    draft: GrammarDraft,
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
) -> list[GrammarNote]:
    """归一化 grammar_notes。"""
    result: list[GrammarNote] = []
    seen_keys: set[str] = set()

    for g in draft.grammar_notes:
        # 所有 span 都必须 grounding
        all_valid = True
        for span in g.spans:
            if not _grounding_check("grammar_note", span.text, g.sentence_id, ctx.sentence_map, "grammar", drop_log):
                all_valid = False
                break

        if not all_valid:
            continue

        # 去重（基于第一个 span）
        primary_text = g.spans[0].text if g.spans else ""
        key = _make_anchor_key("grammar_note", g.sentence_id, primary_text)
        if key in seen_keys:
            _log_drop(
                "grammar", "grammar_note", g.sentence_id, primary_text,
                "duplicate", "deduplication", drop_log
            )
            continue
        seen_keys.add(key)
        result.append(g)

    return result


def _normalize_sentence_analyses(
    draft: GrammarDraft,
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
) -> list[SentenceAnalysis]:
    """归一化 sentence_analyses。"""
    result: list[SentenceAnalysis] = []
    seen_keys: set[str] = set()

    for s in draft.sentence_analyses:
        # Chunks grounding 检查（chunks 为可选）
        all_valid = True
        if s.chunks:
            for chunk in s.chunks:
                if not _grounding_check("sentence_analysis", chunk.text, s.sentence_id, ctx.sentence_map, "grammar", drop_log):
                    all_valid = False
                    break

        if not all_valid:
            continue

        # 去重
        key = _make_anchor_key("sentence_analysis", s.sentence_id, s.label)
        if key in seen_keys:
            _log_drop(
                "grammar", "sentence_analysis", s.sentence_id, s.label,
                "duplicate", "deduplication", drop_log
            )
            continue
        seen_keys.add(key)
        result.append(s)

    return result


def _merge_and_resolve_conflicts(
    vocab_result: list[VocabHighlight],
    phrase_result: list[PhraseGloss],
    context_result: list[ContextGloss],
    grammar_result: list[GrammarNote],
    sentence_analysis_result: list[SentenceAnalysis],
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
) -> list[Annotation]:
    """合并所有标注并消解冲突。

    冲突消解规则：
    - 同一句子中，同一锚点文本，context_gloss > phrase_gloss > vocab_highlight
    - grammar_note 与词汇类不互斥，保留
    - sentence_analysis 独立存在
    """
    # 按优先级排序后的词汇类标注
    merged: list[Annotation] = []

    # 先加入 grammar_note 和 sentence_analysis（它们不与其他类冲突）
    merged.extend(grammar_result)
    merged.extend(sentence_analysis_result)

    # 构建词汇类标注的锚点集合（用于冲突检测）
    # key: (sentence_id, anchor_text)
    vocab_marks: dict[tuple[str, str], tuple[int, VocabHighlight]] = {}
    phrase_marks: dict[tuple[str, str], tuple[int, PhraseGloss]] = {}
    context_marks: dict[tuple[str, str], tuple[int, ContextGloss]] = {}

    for v in vocab_result:
        key = (v.sentence_id, v.text)
        vocab_marks[key] = (PRIORITY_RANK["vocab_highlight"], v)

    for p in phrase_result:
        key = (p.sentence_id, p.text)
        phrase_marks[key] = (PRIORITY_RANK["phrase_gloss"], p)

    for c in context_result:
        key = (c.sentence_id, c.text)
        context_marks[key] = (PRIORITY_RANK["context_gloss"], c)

    # 冲突消解：对于同一 (sentence_id, text)，只保留优先级最高的
    all_keys = set(vocab_marks.keys()) | set(phrase_marks.keys()) | set(context_marks.keys())

    for key in all_keys:
        sentence_id, text = key
        candidates: list[tuple[int, Annotation]] = []

        if key in vocab_marks:
            candidates.append(vocab_marks[key])
        if key in phrase_marks:
            candidates.append(phrase_marks[key])
        if key in context_marks:
            candidates.append(context_marks[key])

        # 按优先级排序，保留最高的
        candidates.sort(key=lambda x: x[0], reverse=True)
        winner = candidates[0][1]
        merged.append(winner)

        # 记录被消解的
        for _, annotation in candidates[1:]:
            _log_drop(
                "vocabulary" if annotation.type in ("vocab_highlight", "phrase_gloss", "context_gloss") else "grammar",
                annotation.type,
                annotation.sentence_id,
                text,
                "conflict_resolution",  # will be fixed in next step
                "conflict_resolution",
                drop_log
            )

    return merged


def _density_control(
    annotations: list[Annotation],
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
    max_per_sentence: int = 8,
) -> list[Annotation]:
    """同句密度控制。

    超过 max_per_sentence 的标注，按优先级保留。
    """
    # 统计每句标注数
    sentence_counts: dict[str, list[tuple[int, Annotation]]] = {}

    for ann in annotations:
        priority = PRIORITY_RANK.get(ann.type, 0)
        if ann.sentence_id not in sentence_counts:
            sentence_counts[ann.sentence_id] = []
        sentence_counts[ann.sentence_id].append((priority, ann))

    # 对每句超过阈值的，裁剪低优先级
    result: list[Annotation] = []

    for ann in annotations:
        sentence_id = ann.sentence_id
        count = len(sentence_counts.get(sentence_id, []))

        if count <= max_per_sentence:
            result.append(ann)
            continue

        # 超过阈值，检查是否在 top max_per_sentence 中
        sorted_anns = sorted(sentence_counts[sentence_id], key=lambda x: x[0], reverse=True)
        top_anns = {a.sentence_id + "_" + getattr(a, 'text', getattr(a, 'label', '')) for _, a in sorted_anns[:max_per_sentence]}

        ann_key = sentence_id + "_" + getattr(ann, 'text', getattr(ann, 'label', ''))
        if ann_key in top_anns:
            result.append(ann)
        else:
            _log_drop(
                "vocabulary" if ann.type in ("vocab_highlight", "phrase_gloss", "context_gloss") else "grammar",
                ann.type,
                sentence_id,
                getattr(ann, 'text', getattr(ann, 'label', '')),
                f"density_exceeded_max_{max_per_sentence}",
                "density_control",
                drop_log
            )

    return result


def _normalize_translations(
    draft: TranslationDraft,
    ctx: NormalizationContext,
    drop_log: list[DropLogEntry],
) -> list[SentenceTranslation]:
    """归一化翻译。"""
    result: list[SentenceTranslation] = []
    seen_ids: set[str] = set()

    for t in draft.sentence_translations:
        # 检查 sentence_id 是否有效
        if t.sentence_id not in ctx.sentence_map:
            _log_drop(
                "translation", "sentence_translation", t.sentence_id, "",
                "sentence_id_not_found", "grounding", drop_log
            )
            continue

        # 检查翻译是否为空
        if not t.translation_zh.strip():
            _log_drop(
                "translation", "sentence_translation", t.sentence_id, "",
                "empty_translation", "pruning", drop_log
            )
            continue

        # 去重
        if t.sentence_id in seen_ids:
            _log_drop(
                "translation", "sentence_translation", t.sentence_id, "",
                "duplicate", "deduplication", drop_log
            )
            continue

        seen_ids.add(t.sentence_id)
        result.append(t)

    return result


def normalize_and_ground(
    vocabulary_draft: VocabularyDraft,
    grammar_draft: GrammarDraft,
    translation_draft: TranslationDraft,
    sentences: list[PreparedSentence],
) -> NormalizedAnnotationResult:
    """主归一化函数。

    合并三个 agent 的 draft，输出归一化结果。
    """
    # 构建上下文
    ctx = NormalizationContext(
        sentences=sentences,
        sentence_map={s.sentence_id: s for s in sentences},
    )

    # Drop log
    drop_log: list[DropLogEntry] = []

    # 基础校验（记录 warning）
    validate_all_drafts(vocabulary_draft, grammar_draft, translation_draft, sentences)

    # 归一化各类型
    vocab_result = _normalize_vocab_highlights(vocabulary_draft, ctx, drop_log)
    phrase_result = _normalize_phrase_glosses(vocabulary_draft, ctx, drop_log)
    context_result = _normalize_context_glosses(vocabulary_draft, ctx, drop_log)
    grammar_result = _normalize_grammar_notes(grammar_draft, ctx, drop_log)
    sentence_analysis_result = _normalize_sentence_analyses(grammar_draft, ctx, drop_log)
    translation_result = _normalize_translations(translation_draft, ctx, drop_log)

    # 合并并消解冲突
    merged_annotations = _merge_and_resolve_conflicts(
        vocab_result, phrase_result, context_result,
        grammar_result, sentence_analysis_result,
        ctx, drop_log
    )

    # 密度控制
    final_annotations = _density_control(merged_annotations, ctx, drop_log=drop_log)

    return NormalizedAnnotationResult(
        annotations=final_annotations,
        sentence_translations=translation_result,
        drop_log=drop_log,
    )

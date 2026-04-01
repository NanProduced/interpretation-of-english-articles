from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from app.schemas.analysis import (
    AnalysisCard,
    AnalyzeRequestMeta,
    ArticleParagraph,
    ArticleSentence,
    ArticleStructure,
    InlineMark,
    InlineMarkAnchorMultiText,
    InlineMarkAnchorText,
    RenderSceneModel,
    SentenceEntry,
    TranslationItem,
)
from app.schemas.internal.analysis import (
    CardDraft,
    InlineMarkDraft,
    MultiTextAnchor,
    MultiTextPart,
    PreparedInput,
    SentenceDraft,
    SentenceEntryDraft,
    SentenceTranslationDraft,
    TeachingOutput,
    TextAnchor,
    UserRules,
)
from app.services.analysis.anchor_resolution import (
    resolve_multi_text_anchor,
    resolve_text_anchor,
)

LOW_VALUE_VOCABULARY = {
    "this",
    "that",
    "these",
    "those",
    "there",
    "which",
    "where",
    "while",
    "about",
    "because",
}


@dataclass
class AssemblyOutcome:
    result: RenderSceneModel
    dropped_count: int


def _stable_id(prefix: str, payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _is_low_value_vocabulary(anchor_text: str) -> bool:
    stripped = anchor_text.strip().strip("\"'""''")
    lowered = stripped.lower()
    if not stripped:
        return True
    if lowered in LOW_VALUE_VOCABULARY:
        return True
    if len(stripped) < 4:
        return True
    tokens = [token for token in stripped.replace("-", " ").split() if token]
    if tokens and all(token[:1].isupper() for token in tokens if token[:1].isalpha()):
        return True
    return False


def _build_article(prepared_input: PreparedInput, source_type: str) -> ArticleStructure:
    return ArticleStructure(
        source_type=source_type,
        source_text=prepared_input.source_text,
        render_text=prepared_input.render_text,
        paragraphs=[
            ArticleParagraph(
                paragraph_id=paragraph.paragraph_id,
                text=paragraph.text,
                render_span=paragraph.render_span,
                sentence_ids=paragraph.sentence_ids,
            )
            for paragraph in prepared_input.paragraphs
        ],
        sentences=[
            ArticleSentence(
                sentence_id=sentence.sentence_id,
                paragraph_id=sentence.paragraph_id,
                text=sentence.text,
                sentence_span=sentence.sentence_span,
            )
            for sentence in prepared_input.sentences
        ],
    )


def _resolve_inline_mark_anchor(
    sentence_map: dict[str, SentenceDraft],
    draft: InlineMarkDraft,
) -> InlineMarkAnchorText | InlineMarkAnchorMultiText | None:
    """将 InlineMarkDraft 的 anchor 解析为前端使用的 InlineMarkAnchor 格式。"""
    anchor = draft.anchor

    if isinstance(anchor, TextAnchor):
        sentence = sentence_map.get(anchor.sentence_id)
        if sentence is None:
            return None
        return InlineMarkAnchorText(
            kind="text",
            sentence_id=anchor.sentence_id,
            anchor_text=anchor.anchor_text,
            occurrence=anchor.occurrence,
        )

    if isinstance(anchor, MultiTextAnchor):
        sentence = sentence_map.get(anchor.sentence_id)
        if sentence is None:
            return None

        parts = [
            {
                "anchor_text": part.anchor_text,
                "occurrence": part.occurrence,
                "role": part.role,
            }
            for part in anchor.parts
        ]
        # 验证多段锚点可以解析
        resolved = resolve_multi_text_anchor(sentence, parts)
        if resolved is None:
            return None

        return InlineMarkAnchorMultiText(
            kind="multi_text",
            sentence_id=anchor.sentence_id,
            parts=[
                MultiTextPart(
                    anchor_text=part.anchor_text,
                    occurrence=part.occurrence,
                    role=part.role,
                )
                for part in anchor.parts
            ],
        )

    return None


def assemble_result(
    *,
    request_id: str,
    source_type: str,
    reading_goal: str,
    reading_variant: str,
    prepared_input: PreparedInput,
    user_rules: UserRules,
    teaching_output: TeachingOutput,
) -> AssemblyOutcome:
    sentence_map: dict[str, SentenceDraft] = {
        sentence.sentence_id: sentence for sentence in prepared_input.sentences
    }
    dropped_count = 0

    # 处理 inline_marks
    inline_marks: list[InlineMark] = []
    for draft in teaching_output.inline_marks:
        # 过滤低价值词汇
        if draft.tone in ("phrase", "exam", "focus"):
            anchor_text = ""
            if isinstance(draft.anchor, TextAnchor):
                anchor_text = draft.anchor.anchor_text
            elif isinstance(draft.anchor, MultiTextAnchor):
                # 取第一部分的文本
                if draft.anchor.parts:
                    anchor_text = draft.anchor.parts[0].anchor_text

            if anchor_text and _is_low_value_vocabulary(anchor_text):
                dropped_count += 1
                continue

        resolved_anchor = _resolve_inline_mark_anchor(sentence_map, draft)
        if resolved_anchor is None:
            dropped_count += 1
            continue

        inline_mark = InlineMark(
            id=_stable_id(
                "im",
                {
                    "anchor": resolved_anchor.model_dump(mode="json"),
                    "tone": draft.tone,
                    "render_type": draft.render_type,
                    "clickable": draft.clickable,
                    "ai_note": draft.ai_note,
                    "lookup_text": draft.lookup_text,
                    "lookup_kind": draft.lookup_kind,
                    "ai_title": draft.ai_title,
                    "ai_body": draft.ai_body,
                },
            ),
            anchor=resolved_anchor,
            tone=draft.tone,
            render_type=draft.render_type,
            clickable=draft.clickable,
            ai_note=draft.ai_note,
            lookup_text=draft.lookup_text,
            lookup_kind=draft.lookup_kind,
            ai_title=draft.ai_title,
            ai_body=draft.ai_body,
        )
        inline_marks.append(inline_mark)

    # 处理 sentence_entries
    sentence_entries: list[SentenceEntry] = []
    for draft in teaching_output.sentence_entries:
        if draft.sentence_id not in sentence_map:
            dropped_count += 1
            continue
        sentence_entries.append(
            SentenceEntry(
                id=_stable_id(
                    "se",
                    {
                        "sentence_id": draft.sentence_id,
                        "label": draft.label,
                        "entry_type": draft.entry_type,
                        "title": draft.title,
                        "content": draft.content,
                    },
                ),
                sentence_id=draft.sentence_id,
                label=draft.label,
                entry_type=draft.entry_type,
                title=draft.title,
                content=draft.content,
            )
        )

    # 处理 cards
    cards: list[AnalysisCard] = []
    for draft in teaching_output.cards:
        if draft.after_sentence_id not in sentence_map:
            dropped_count += 1
            continue
        cards.append(
            AnalysisCard(
                id=_stable_id(
                    "ac",
                    {
                        "after_sentence_id": draft.after_sentence_id,
                        "title": draft.title,
                        "content": draft.content,
                    },
                ),
                after_sentence_id=draft.after_sentence_id,
                title=draft.title,
                content=draft.content,
            )
        )

    # 处理 translations
    translations: list[TranslationItem] = [
        TranslationItem(
            sentence_id=t.sentence_id,
            translation_zh=t.translation_zh,
        )
        for t in teaching_output.sentence_translations
    ]

    # 验证翻译覆盖
    expected_sentence_ids = {sentence.sentence_id for sentence in prepared_input.sentences}
    translated_sentence_ids = {t.sentence_id for t in translations}
    if translated_sentence_ids != expected_sentence_ids:
        missing_count = len(expected_sentence_ids - translated_sentence_ids)
        raise ValueError(f"sentence translation coverage mismatch: missing={missing_count}")

    article = _build_article(prepared_input, source_type)

    result = RenderSceneModel(
        request=AnalyzeRequestMeta(
            request_id=request_id,
            source_type=source_type,
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            profile_id=user_rules.profile_id,
        ),
        article=article,
        translations=translations,
        inline_marks=inline_marks,
        sentence_entries=sentence_entries,
        cards=cards,
    )
    return AssemblyOutcome(result=result, dropped_count=dropped_count)

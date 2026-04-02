"""Draft validators for V3 parallel agent outputs.

每个 agent 产出 draft 后，进入 normalize_and_ground 前需要做基础校验。
校验失败不直接拒绝，而是记录 warning 并允许继续。
"""

from __future__ import annotations

from app.schemas.internal.analysis import PreparedSentence
from app.schemas.internal.drafts import GrammarDraft, TranslationDraft, VocabularyDraft


class DraftValidationError(Exception):
    """校验失败异常。"""

    def __init__(self, message: str, draft_type: str, sentence_id: str | None = None):
        self.message = message
        self.draft_type = draft_type
        self.sentence_id = sentence_id
        super().__init__(self.message)


def validate_vocabulary_draft(
    draft: VocabularyDraft,
    sentences: list[PreparedSentence],
) -> list[str]:
    """校验 vocabulary draft。

    返回 warning 消息列表。
    """
    warnings: list[str] = []
    sentence_map = {s.sentence_id: s for s in sentences}

    for v in draft.vocab_highlights:
        if v.sentence_id not in sentence_map:
            warnings.append(f"vocab_highlight: sentence_id {v.sentence_id} not found")
            continue
        sent_text = sentence_map[v.sentence_id].text
        if v.text not in sent_text:
            warnings.append(
                f"vocab_highlight: text '{v.text}' not found in sentence {v.sentence_id}"
            )

    for p in draft.phrase_glosses:
        if p.sentence_id not in sentence_map:
            warnings.append(f"phrase_gloss: sentence_id {p.sentence_id} not found")
            continue
        sent_text = sentence_map[p.sentence_id].text
        if p.text not in sent_text:
            warnings.append(
                f"phrase_gloss: text '{p.text}' not found in sentence {p.sentence_id}"
            )

    for c in draft.context_glosses:
        if c.sentence_id not in sentence_map:
            warnings.append(f"context_gloss: sentence_id {c.sentence_id} not found")
            continue
        sent_text = sentence_map[c.sentence_id].text
        if c.text not in sent_text:
            warnings.append(
                f"context_gloss: text '{c.text}' not found in sentence {c.sentence_id}"
            )

    return warnings


def validate_grammar_draft(
    draft: GrammarDraft,
    sentences: list[PreparedSentence],
) -> list[str]:
    """校验 grammar draft。

    返回 warning 消息列表。
    """
    warnings: list[str] = []
    sentence_map = {s.sentence_id: s for s in sentences}

    for g in draft.grammar_notes:
        if g.sentence_id not in sentence_map:
            warnings.append(f"grammar_note: sentence_id {g.sentence_id} not found")
            continue
        sent_text = sentence_map[g.sentence_id].text
        for span in g.spans:
            if span.text not in sent_text:
                warnings.append(
                    f"grammar_note: span text '{span.text}' not found in sentence {g.sentence_id}"
                )

    for s in draft.sentence_analyses:
        if s.sentence_id not in sentence_map:
            warnings.append(f"sentence_analysis: sentence_id {s.sentence_id} not found")
            continue
        sent_text = sentence_map[s.sentence_id].text
        if s.chunks:
            for chunk in s.chunks:
                if chunk.text not in sent_text:
                    warnings.append(
                        f"sentence_analysis: chunk text '{chunk.text}' "
                        f"not found in sentence {s.sentence_id}"
                    )

    return warnings


def validate_translation_draft(
    draft: TranslationDraft,
    sentences: list[PreparedSentence],
) -> list[str]:
    """校验 translation draft。

    返回 warning 消息列表。
    翻译缺失应有 warning，不允许静默吞掉。
    """
    warnings: list[str] = []
    sentence_ids = {s.sentence_id for s in sentences}
    translated_ids = {t.sentence_id for t in draft.sentence_translations}

    missing = sentence_ids - translated_ids
    if missing:
        warnings.append(f"translation missing for sentence_ids: {sorted(missing)}")

    for t in draft.sentence_translations:
        if t.sentence_id not in sentence_ids:
            warnings.append(f"translation: sentence_id {t.sentence_id} not found in sentences")
        if not t.translation_zh.strip():
            warnings.append(f"translation: empty translation for sentence_id {t.sentence_id}")

    return warnings


def validate_all_drafts(
    vocabulary_draft: VocabularyDraft,
    grammar_draft: GrammarDraft,
    translation_draft: TranslationDraft,
    sentences: list[PreparedSentence],
) -> list[str]:
    """一次性校验所有 draft。

    返回所有 warning 的合并列表。
    """
    all_warnings: list[str] = []
    all_warnings.extend(validate_vocabulary_draft(vocabulary_draft, sentences))
    all_warnings.extend(validate_grammar_draft(grammar_draft, sentences))
    all_warnings.extend(validate_translation_draft(translation_draft, sentences))
    return all_warnings

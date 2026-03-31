from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from app.schemas.analysis import (
    AnalysisMetrics,
    AnalysisResult,
    AnalysisStatus,
    AnalysisTranslations,
    AnalysisWarning,
    AnalyzeRequestMeta,
    ArticleParagraph,
    ArticleSentence,
    ArticleStructure,
    GrammarAnnotation,
    RenderMark,
    SanitizeReport,
    SentenceAnnotation,
    SentenceTranslation,
    VocabularyAnnotation,
)
from app.schemas.common import TextSpan
from app.schemas.internal.analysis import (
    AnnotationDraft,
    DisplayGroup,
    DisplayMode,
    DisplayPriority,
    PreparedInput,
    SentenceDraft,
    TeachingOutput,
    UserRules,
)
from app.services.analysis.anchor_resolution import resolve_anchor

AnnotationKind: TypeAlias = Literal["vocabulary", "grammar", "sentence_note"]
ResolvedAnnotation: TypeAlias = tuple[AnnotationKind, AnnotationDraft, TextSpan]

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
    result: AnalysisResult
    dropped_count: int


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


def _display_priority(pedagogy_level: str) -> DisplayPriority:
    priority_map: dict[str, DisplayPriority] = {
        "core": "primary",
        "support": "secondary",
        "advanced": "tertiary",
    }
    return priority_map[pedagogy_level]


def _display_group(pedagogy_level: str) -> DisplayGroup:
    if pedagogy_level == "advanced":
        return "advanced"
    if pedagogy_level == "support":
        return "support"
    return "core"


def _default_visible(pedagogy_level: str, user_rules: UserRules) -> bool:
    if pedagogy_level == "advanced" and user_rules.presentation_policy.advanced_default_collapsed:
        return False
    return True


def _display_mode(annotation_type: AnnotationKind, user_rules: UserRules) -> DisplayMode:
    if annotation_type == "vocabulary":
        return user_rules.presentation_policy.vocabulary_display_mode
    if annotation_type == "grammar":
        return user_rules.presentation_policy.grammar_display_mode
    return user_rules.presentation_policy.sentence_display_mode


def _is_low_value_vocabulary(anchor_text: str) -> bool:
    stripped = anchor_text.strip().strip("\"'“”‘’")
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


def _build_full_translation(
    paragraphs: list[ArticleParagraph],
    sentence_map: dict[str, SentenceTranslation],
) -> str:
    paragraph_texts: list[str] = []
    for paragraph in paragraphs:
        pieces = [
            sentence_map[sentence_id].translation_zh
            for sentence_id in paragraph.sentence_ids
            if sentence_id in sentence_map
        ]
        if pieces:
            paragraph_texts.append(" ".join(pieces))
    return "\n\n".join(paragraph_texts)


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
    warnings: list[AnalysisWarning] = []
    dropped_count = 0
    resolved_annotations: list[ResolvedAnnotation] = []

    def add_annotations(annotation_type: AnnotationKind, drafts: list[AnnotationDraft]) -> None:
        nonlocal dropped_count
        for draft in drafts:
            sentence = sentence_map.get(draft.sentence_id)
            if sentence is None:
                dropped_count += 1
                warnings.append(
                    AnalysisWarning(
                        code="UNKNOWN_SENTENCE_ID",
                        message_zh="存在无法映射到正文句子的标注，已自动丢弃。",
                    )
                )
                continue
            if annotation_type == "vocabulary" and _is_low_value_vocabulary(draft.anchor_text):
                dropped_count += 1
                continue

            # 只允许在句内解析锚点，避免把模型返回的字符串直接当成全文坐标。
            render_span = resolve_anchor(sentence, draft.anchor_text, draft.anchor_occurrence)
            if render_span is None:
                dropped_count += 1
                warnings.append(
                    AnalysisWarning(
                        code="ANCHOR_RESOLUTION_FAILED",
                        message_zh="存在无法定位到正文的标注锚点，已自动丢弃。",
                    )
                )
                continue
            resolved_annotations.append((annotation_type, draft, render_span))

    add_annotations("vocabulary", teaching_output.vocabulary_annotations)
    add_annotations("grammar", teaching_output.grammar_annotations)
    add_annotations("sentence_note", teaching_output.sentence_annotations)

    resolved_annotations.sort(key=lambda item: (item[2].start, item[0], item[1].title))

    vocabulary_annotations: list[VocabularyAnnotation] = []
    grammar_annotations: list[GrammarAnnotation] = []
    sentence_annotations: list[SentenceAnnotation] = []
    render_marks: list[RenderMark] = []

    for index, (annotation_type, draft, render_span) in enumerate(resolved_annotations, start=1):
        annotation_id = f"a{index}"
        display_priority = _display_priority(draft.pedagogy_level)
        display_group = _display_group(draft.pedagogy_level)
        is_default_visible = _default_visible(draft.pedagogy_level, user_rules)
        common_payload = {
            "annotation_id": annotation_id,
            "sentence_id": draft.sentence_id,
            "anchor_text": draft.anchor_text,
            "render_span": render_span,
            "title": draft.title,
            "content": draft.content,
            "pedagogy_level": draft.pedagogy_level,
            "display_priority": display_priority,
            "display_group": display_group,
            "is_default_visible": is_default_visible,
            "render_index": index,
        }
        if annotation_type == "vocabulary":
            vocabulary_annotations.append(VocabularyAnnotation(**common_payload))
        elif annotation_type == "grammar":
            grammar_annotations.append(GrammarAnnotation(**common_payload))
        else:
            sentence_annotations.append(SentenceAnnotation(**common_payload))

        render_marks.append(
            RenderMark(
                mark_id=f"m{index}",
                annotation_id=annotation_id,
                display_mode=_display_mode(annotation_type, user_rules),
                display_priority=display_priority,
                display_group=display_group,
                render_index=index,
                render_span=render_span,
            )
        )

    sentence_translations = [
        SentenceTranslation(**translation.model_dump())
        for translation in teaching_output.sentence_translations
    ]
    expected_sentence_ids = {sentence.sentence_id for sentence in prepared_input.sentences}
    translated_sentence_ids = {translation.sentence_id for translation in sentence_translations}
    if translated_sentence_ids != expected_sentence_ids:
        missing_count = len(expected_sentence_ids - translated_sentence_ids)
        raise ValueError(f"sentence translation coverage mismatch: missing={missing_count}")

    article = _build_article(prepared_input, source_type)
    full_translation = _build_full_translation(
        article.paragraphs,
        {item.sentence_id: item for item in sentence_translations},
    )

    status = AnalysisStatus(state="success", is_degraded=dropped_count > 0)
    if dropped_count > 0:
        warnings.append(
            AnalysisWarning(
                code="ANNOTATION_DROPPED",
                message_zh="部分标注在本地校验中被丢弃，已保留其余可信结果。",
            )
        )

    result = AnalysisResult(
        request=AnalyzeRequestMeta(
            request_id=request_id,
            source_type=source_type,
            reading_goal=reading_goal,
            reading_variant=reading_variant,
            profile_id=user_rules.profile_id,
        ),
        status=status,
        article=article,
        sanitize_report=SanitizeReport.model_validate(
            prepared_input.sanitize_report.model_dump()
        ),
        vocabulary_annotations=vocabulary_annotations,
        grammar_annotations=grammar_annotations,
        sentence_annotations=sentence_annotations,
        render_marks=render_marks,
        translations=AnalysisTranslations(
            sentence_translations=sentence_translations,
            full_translation_zh=full_translation,
        ),
        warnings=warnings,
        metrics=AnalysisMetrics(
            vocabulary_count=len(vocabulary_annotations),
            grammar_count=len(grammar_annotations),
            sentence_note_count=len(sentence_annotations),
            render_mark_count=len(render_marks),
            sentence_count=len(article.sentences),
            paragraph_count=len(article.paragraphs),
        ),
    )
    return AssemblyOutcome(result=result, dropped_count=dropped_count)

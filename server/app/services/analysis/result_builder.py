from __future__ import annotations

from app.schemas.analysis import (
    AnalysisAnnotations,
    AnalysisMetrics,
    AnalysisResult,
    AnalysisTranslations,
    AnalyzeRequestMeta,
    DifficultSentenceAnnotation,
    GrammarAnnotation,
    VocabularyAnnotation,
)
from app.schemas.internal.analysis import CoreAgentOutput, TranslationAgentOutput
from app.schemas.preprocess import PreprocessResult
from app.services.analysis.article import build_article, infer_sentence_difficulties


def build_merged_result(
    *,
    preprocess: PreprocessResult,
    payload,
    status,
    warnings,
    core_output: CoreAgentOutput,
    translation_output: TranslationAgentOutput,
) -> AnalysisResult:
    article = build_article(preprocess, infer_sentence_difficulties(preprocess, core_output.difficult_sentences))
    annotations = AnalysisAnnotations(
        vocabulary=[
            VocabularyAnnotation(
                annotation_id=item.annotation_id,
                surface=item.surface,
                lemma=item.lemma,
                span=item.span,
                sentence_id=item.sentence_id,
                phrase_type=item.phrase_type,
                context_gloss_zh=item.context_gloss_zh,
                short_explanation_zh=item.short_explanation_zh,
                objective_level=item.objective_level,
                priority="reference",
                default_visible=False,
                exam_tags=item.exam_tags,
                scene_tags=item.scene_tags,
            )
            for item in core_output.vocabulary
        ],
        grammar=[
            GrammarAnnotation(
                annotation_id=item.annotation_id,
                type=item.type,
                sentence_id=item.sentence_id,
                span=item.span,
                label=item.label,
                short_explanation_zh=item.short_explanation_zh,
                components=item.components,
                objective_level=item.objective_level,
                priority="reference",
                default_visible=False,
            )
            for item in core_output.grammar
        ],
        difficult_sentences=[
            DifficultSentenceAnnotation(
                annotation_id=item.annotation_id,
                sentence_id=item.sentence_id,
                span=item.span,
                trigger_reason=item.trigger_reason,
                main_clause=item.main_clause,
                chunks=item.chunks,
                reading_path_zh=item.reading_path_zh,
                objective_level=item.objective_level,
                priority="reference",
                default_visible=False,
            )
            for item in core_output.difficult_sentences
        ],
    )
    translations = AnalysisTranslations(
        sentence_translations=translation_output.sentence_translations,
        full_translation_zh=translation_output.full_translation_zh,
        key_phrase_translations=translation_output.key_phrase_translations,
    )
    return AnalysisResult(
        request=AnalyzeRequestMeta(
            request_id=preprocess.request.request_id,
            profile_key=preprocess.request.profile_key,
            source_type=preprocess.request.source_type,
            discourse_enabled=payload.discourse_enabled,
        ),
        status=status,
        article=article,
        annotations=annotations,
        translations=translations,
        warnings=warnings,
        metrics=AnalysisMetrics(
            vocabulary_count=len(annotations.vocabulary),
            grammar_count=len(annotations.grammar),
            difficult_sentence_count=len(annotations.difficult_sentences),
            sentence_count=len(article.sentences),
            paragraph_count=len(article.paragraphs),
        ),
    )


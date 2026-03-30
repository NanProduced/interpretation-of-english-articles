from __future__ import annotations

from app.schemas.analysis import (
    ArticleParagraph,
    ArticleSentence,
    ArticleStructure,
    SentenceDifficultyAssessment,
)
from app.schemas.internal.analysis import CoreDifficultSentenceAnnotation
from app.schemas.preprocess import PreprocessResult


def build_article(preprocess: PreprocessResult, difficulties: list[SentenceDifficultyAssessment]) -> ArticleStructure:
    difficulty_map = {item.sentence_id: item for item in difficulties}

    paragraphs = [
        ArticleParagraph(
            paragraph_id=paragraph.paragraph_id,
            text=paragraph.text,
            start=paragraph.start,
            end=paragraph.end,
            sentence_ids=[
                sentence.sentence_id
                for sentence in preprocess.segmentation.sentences
                if sentence.paragraph_id == paragraph.paragraph_id
            ],
        )
        for paragraph in preprocess.segmentation.paragraphs
    ]

    sentences: list[ArticleSentence] = []
    for sentence in preprocess.segmentation.sentences:
        difficulty = difficulty_map.get(
            sentence.sentence_id,
            SentenceDifficultyAssessment(
                sentence_id=sentence.sentence_id,
                difficulty_score=0.3,
                is_difficult=False,
            ),
        )
        sentences.append(
            ArticleSentence(
                sentence_id=sentence.sentence_id,
                paragraph_id=sentence.paragraph_id,
                text=sentence.text,
                start=sentence.start,
                end=sentence.end,
                difficulty_score=difficulty.difficulty_score,
                is_difficult=difficulty.is_difficult,
            )
        )

    return ArticleStructure(
        source_type=preprocess.request.source_type,
        source_text=preprocess.normalized.source_text,
        render_text=preprocess.normalized.clean_text,
        paragraphs=paragraphs,
        sentences=sentences,
    )


def infer_sentence_difficulties(
    preprocess: PreprocessResult,
    difficult_sentences: list[CoreDifficultSentenceAnnotation],
) -> list[SentenceDifficultyAssessment]:
    difficult_ids = {item.sentence_id for item in difficult_sentences}
    assessments: list[SentenceDifficultyAssessment] = []
    for sentence in preprocess.segmentation.sentences:
        is_difficult = sentence.sentence_id in difficult_ids
        assessments.append(
            SentenceDifficultyAssessment(
                sentence_id=sentence.sentence_id,
                difficulty_score=0.78 if is_difficult else 0.32,
                is_difficult=is_difficult,
            )
        )
    return assessments


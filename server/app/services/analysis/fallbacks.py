from __future__ import annotations

import re

from app.schemas.common import TextSpan
from app.schemas.internal.analysis import (
    CoreAgentOutput,
    CoreDifficultSentenceAnnotation,
    CoreGrammarAnnotation,
    CoreVocabularyAnnotation,
    DifficultSentenceChunk,
    KeyPhraseTranslation,
    SentenceComponent,
    SentenceTranslation,
    TranslationAgentOutput,
)
from app.schemas.preprocess import PreprocessResult

WORD_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z'-]{3,}\b")
COMMON_WORDS = {
    "this",
    "that",
    "with",
    "from",
    "have",
    "they",
    "their",
    "there",
    "which",
    "while",
    "would",
    "about",
    "could",
    "these",
    "those",
    "into",
    "than",
    "because",
    "through",
}


def find_span(render_text: str, snippet: str) -> TextSpan | None:
    if not snippet:
        return None
    start = render_text.find(snippet)
    if start < 0:
        return None
    return TextSpan(start=start, end=start + len(snippet))


def fallback_core(preprocess: PreprocessResult) -> CoreAgentOutput:
    render_text = preprocess.normalized.clean_text
    vocabulary: list[CoreVocabularyAnnotation] = []
    grammar: list[CoreGrammarAnnotation] = []
    difficult_sentences: list[CoreDifficultSentenceAnnotation] = []

    candidate_words: list[tuple[str, str, TextSpan]] = []
    for sentence in preprocess.segmentation.sentences:
        for match in WORD_PATTERN.finditer(sentence.text):
            word = match.group(0)
            normalized = word.lower()
            if normalized in COMMON_WORDS or len(normalized) < 6:
                continue
            absolute_start = sentence.start + match.start()
            candidate_words.append(
                (
                    sentence.sentence_id,
                    word,
                    TextSpan(start=absolute_start, end=absolute_start + len(word)),
                )
            )

    for index, (sentence_id, surface, span) in enumerate(candidate_words[:8], start=1):
        vocabulary.append(
            CoreVocabularyAnnotation(
                annotation_id=f"v{index}",
                surface=surface,
                lemma=surface.lower(),
                span=span,
                sentence_id=sentence_id,
                phrase_type="word",
                context_gloss_zh=f"{surface} 在当前语境中是需要重点关注的词。",
                short_explanation_zh="这是 fallback 生成的简化说明，后续会由正式 agent 提供更稳定解释。",
                objective_level="intermediate" if len(surface) >= 8 else "basic",
            )
        )

    grammar_index = 1
    for sentence in preprocess.segmentation.sentences:
        lowered = sentence.text.lower()
        if " which " in lowered or " that " in lowered:
            grammar.append(
                CoreGrammarAnnotation(
                    annotation_id=f"g{grammar_index}",
                    type="grammar_point",
                    sentence_id=sentence.sentence_id,
                    span=TextSpan(start=sentence.start, end=sentence.end),
                    label="从句结构",
                    short_explanation_zh="该句包含从句或修饰性结构，阅读时建议先抓主干。",
                    objective_level="intermediate",
                )
            )
            grammar_index += 1

        parts = sentence.text.split(" ", 2)
        if len(parts) >= 2:
            subject_text = " ".join(parts[:1])
            predicate_text = parts[1]
            grammar.append(
                CoreGrammarAnnotation(
                    annotation_id=f"g{grammar_index}",
                    type="sentence_component",
                    sentence_id=sentence.sentence_id,
                    label="句子主干",
                    short_explanation_zh="这里先用简化规则标出主语和谓语，后续会由正式 agent 细化。",
                    components=[
                        SentenceComponent(
                            label="subject",
                            text=subject_text,
                            span=find_span(render_text, subject_text),
                        ),
                        SentenceComponent(
                            label="predicate",
                            text=predicate_text,
                            span=find_span(render_text, predicate_text),
                        ),
                    ],
                    objective_level="basic",
                )
            )
            grammar_index += 1

    difficult_index = 1
    for sentence in preprocess.segmentation.sentences:
        words = WORD_PATTERN.findall(sentence.text)
        is_difficult = len(words) >= 18 or "," in sentence.text or " which " in sentence.text.lower()
        if not is_difficult:
            continue
        chunks = [
            DifficultSentenceChunk(order=order, label=f"意群 {order}", text=chunk.strip())
            for order, chunk in enumerate(sentence.text.split(","), start=1)
            if chunk.strip()
        ]
        difficult_sentences.append(
            CoreDifficultSentenceAnnotation(
                annotation_id=f"d{difficult_index}",
                sentence_id=sentence.sentence_id,
                span=TextSpan(start=sentence.start, end=sentence.end),
                trigger_reason=["long_sentence"] if len(sentence.text.split()) >= 18 else ["embedded_clause"],
                main_clause=chunks[0].text if chunks else sentence.text,
                chunks=chunks or [DifficultSentenceChunk(order=1, label="主干", text=sentence.text)],
                reading_path_zh="先看句子主干，再按逗号或从句边界拆开理解。",
                objective_level="intermediate",
            )
        )
        difficult_index += 1

    return CoreAgentOutput(
        vocabulary=vocabulary,
        grammar=grammar,
        difficult_sentences=difficult_sentences,
    )


def fallback_translation(preprocess: PreprocessResult) -> TranslationAgentOutput:
    sentence_translations = [
        SentenceTranslation(
            sentence_id=sentence.sentence_id,
            translation_zh=f"【待优化翻译】{sentence.text}",
            style="natural",
        )
        for sentence in preprocess.segmentation.sentences
    ]

    key_phrase_translations: list[KeyPhraseTranslation] = []
    for sentence in preprocess.segmentation.sentences[:3]:
        words = WORD_PATTERN.findall(sentence.text)
        if not words:
            continue
        phrase = words[0]
        span = find_span(preprocess.normalized.clean_text, phrase)
        if span is None:
            continue
        key_phrase_translations.append(
            KeyPhraseTranslation(
                phrase=phrase,
                sentence_id=sentence.sentence_id,
                span=span,
                translation_zh=f"{phrase}（待补充）",
            )
        )

    return TranslationAgentOutput(
        sentence_translations=sentence_translations,
        full_translation_zh="【待优化翻译】当前使用 fallback 翻译结果，后续会由正式翻译 agent 输出自然中文。",
        key_phrase_translations=key_phrase_translations,
    )


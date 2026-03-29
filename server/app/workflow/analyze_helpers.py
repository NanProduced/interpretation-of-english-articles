from __future__ import annotations

import re
from typing import Literal

from app.schemas.analysis import (
    AnalysisAnnotations,
    AnalysisMetrics,
    AnalysisResult,
    AnalysisTranslations,
    AnalyzeRequestMeta,
    ArticleParagraph,
    ArticleSentence,
    ArticleStructure,
    CoreAgentOutput,
    CoreDifficultSentenceAnnotation,
    CoreGrammarAnnotation,
    CoreVocabularyAnnotation,
    DifficultSentenceAnnotation,
    DifficultSentenceChunk,
    GrammarAnnotation,
    KeyPhraseTranslation,
    SentenceComponent,
    SentenceDifficultyAssessment,
    SentenceTranslation,
    TranslationAgentOutput,
    VocabularyAnnotation,
)
from app.schemas.preprocess import PreprocessResult, TextSpan


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


def build_article(preprocess: PreprocessResult, difficulties: list[SentenceDifficultyAssessment]) -> ArticleStructure:
    """把 preprocess 输出转换为前端可消费的文章结构。"""
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
    difficult_sentences: list[CoreDifficultSentenceAnnotation] | list[DifficultSentenceAnnotation],
) -> list[SentenceDifficultyAssessment]:
    """根据长难句标注结果回填逐句难度。

    v0 里不再要求 core_agent 为每个句子单独输出 difficulty，避免长文时结构化 JSON 过大。
    """
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


def priority_by_profile(profile_key: str, objective_level: str) -> Literal["core", "expand", "reference"]:
    """把客观难度映射成当前用户 profile 下的展示优先级。

    这里不是“等级越高优先级越高”的简单映射，而是：
    - exam 类 profile：基础和中级内容都视为核心，进阶内容下放到 expand
    - IELTS / TOEFL：进阶内容也可能属于核心，其余保持 expand
    - 其他通用 profile：基础内容放 expand，其余默认 reference
    """
    if profile_key.startswith("exam"):
        if objective_level in {"basic", "intermediate"}:
            return "core"
        return "expand"

    if profile_key in {"ielts", "toefl"}:
        if objective_level == "advanced":
            return "core"
        return "expand"

    if objective_level == "basic":
        return "expand"
    return "reference"


def default_visible_by_priority(priority: str) -> bool:
    """只有 core 级内容默认展开。"""
    return priority == "core"


def find_span(render_text: str, snippet: str) -> TextSpan | None:
    """在渲染文本中定位片段。"""
    if not snippet:
        return None
    start = render_text.find(snippet)
    if start < 0:
        return None
    return TextSpan(start=start, end=start + len(snippet))


def fallback_core(preprocess: PreprocessResult, profile_key: str) -> CoreAgentOutput:
    """核心标注失败时的本地兜底结果。"""
    render_text = preprocess.normalized.clean_text
    vocabulary: list[CoreVocabularyAnnotation] = []
    grammar: list[CoreGrammarAnnotation] = []
    difficult_sentences: list[CoreDifficultSentenceAnnotation] = []

    for sentence in preprocess.segmentation.sentences:
        words = WORD_PATTERN.findall(sentence.text)
        is_difficult = len(words) >= 18 or "," in sentence.text or " which " in sentence.text.lower()
        if not is_difficult:
            continue

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
    """翻译失败时的本地兜底结果。"""
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


def build_merged_result(
    *,
    preprocess: PreprocessResult,
    payload,
    status,
    warnings,
    core_output: CoreAgentOutput,
    translation_output: TranslationAgentOutput,
) -> AnalysisResult:
    """把 preprocess、core、translation 三部分结果组装成最终结构。"""
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

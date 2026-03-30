from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import TextSpan


class SentenceComponent(BaseModel):
    label: Literal[
        "subject",
        "predicate",
        "object",
        "complement",
        "modifier",
        "adverbial",
        "clause",
    ]
    text: str
    span: TextSpan | None = None


class CoreVocabularyAnnotation(BaseModel):
    annotation_id: str
    surface: str
    lemma: str
    span: TextSpan
    sentence_id: str
    phrase_type: Literal["word", "phrase"] = "word"
    context_gloss_zh: str
    short_explanation_zh: str
    objective_level: Literal["basic", "intermediate", "advanced"]
    exam_tags: list[str] = Field(default_factory=list)
    scene_tags: list[str] = Field(default_factory=list)


class CoreGrammarAnnotation(BaseModel):
    annotation_id: str
    type: Literal["grammar_point", "sentence_component", "error_flag"]
    sentence_id: str
    span: TextSpan | None = None
    label: str
    short_explanation_zh: str
    components: list[SentenceComponent] = Field(default_factory=list)
    objective_level: Literal["basic", "intermediate", "advanced"]


class DifficultSentenceChunk(BaseModel):
    order: int = Field(ge=1)
    label: str
    text: str


class CoreDifficultSentenceAnnotation(BaseModel):
    annotation_id: str
    sentence_id: str
    span: TextSpan
    trigger_reason: list[str] = Field(default_factory=list)
    main_clause: str
    chunks: list[DifficultSentenceChunk] = Field(default_factory=list)
    reading_path_zh: str
    objective_level: Literal["basic", "intermediate", "advanced"]


class SentenceTranslation(BaseModel):
    sentence_id: str
    translation_zh: str
    style: Literal["natural", "exam", "literal"] = "natural"


class KeyPhraseTranslation(BaseModel):
    phrase: str
    sentence_id: str
    span: TextSpan
    translation_zh: str


class CoreAgentOutput(BaseModel):
    vocabulary: list[CoreVocabularyAnnotation] = Field(default_factory=list)
    grammar: list[CoreGrammarAnnotation] = Field(default_factory=list)
    difficult_sentences: list[CoreDifficultSentenceAnnotation] = Field(default_factory=list)


class TranslationAgentOutput(BaseModel):
    sentence_translations: list[SentenceTranslation] = Field(default_factory=list)
    full_translation_zh: str
    key_phrase_translations: list[KeyPhraseTranslation] = Field(default_factory=list)


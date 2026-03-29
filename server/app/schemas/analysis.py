from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.preprocess import TextSpan


ANALYSIS_SCHEMA_VERSION = "0.1.0"


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    profile_key: str = "general"
    source_type: Literal["user_input", "daily_article", "ocr"] = "user_input"
    request_id: str | None = None
    discourse_enabled: bool = False


class AnalyzeRequestMeta(BaseModel):
    request_id: str
    profile_key: str
    source_type: Literal["user_input", "daily_article", "ocr"]
    discourse_enabled: bool = False


class AnalysisStatus(BaseModel):
    state: Literal["success", "partial_success", "failed"]
    degraded: bool
    error_code: str | None = None
    user_message: str | None = None


class ArticleParagraph(BaseModel):
    paragraph_id: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    sentence_ids: list[str] = Field(default_factory=list)


class ArticleSentence(BaseModel):
    sentence_id: str
    paragraph_id: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    difficulty_score: float = Field(ge=0.0, le=1.0)
    is_difficult: bool


class ArticleStructure(BaseModel):
    title: str | None = None
    language: Literal["en"] = "en"
    source_type: Literal["user_input", "daily_article", "ocr"]
    source_text: str
    render_text: str
    paragraphs: list[ArticleParagraph] = Field(default_factory=list)
    sentences: list[ArticleSentence] = Field(default_factory=list)


class VocabularyAnnotation(BaseModel):
    annotation_id: str
    type: Literal["vocabulary"] = "vocabulary"
    surface: str
    lemma: str
    span: TextSpan
    sentence_id: str
    phrase_type: Literal["word", "phrase"] = "word"
    context_gloss_zh: str
    short_explanation_zh: str
    objective_level: Literal["basic", "intermediate", "advanced"]
    priority: Literal["core", "expand", "reference"]
    default_visible: bool
    exam_tags: list[str] = Field(default_factory=list)
    scene_tags: list[str] = Field(default_factory=list)


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


class GrammarAnnotation(BaseModel):
    annotation_id: str
    type: Literal["grammar_point", "sentence_component", "error_flag"]
    sentence_id: str
    span: TextSpan | None = None
    label: str
    short_explanation_zh: str
    components: list[SentenceComponent] = Field(default_factory=list)
    objective_level: Literal["basic", "intermediate", "advanced"]
    priority: Literal["core", "expand", "reference"]
    default_visible: bool


class DifficultSentenceChunk(BaseModel):
    order: int = Field(ge=1)
    label: str
    text: str


class DifficultSentenceAnnotation(BaseModel):
    annotation_id: str
    sentence_id: str
    span: TextSpan
    trigger_reason: list[str] = Field(default_factory=list)
    main_clause: str
    chunks: list[DifficultSentenceChunk] = Field(default_factory=list)
    reading_path_zh: str
    objective_level: Literal["basic", "intermediate", "advanced"]
    priority: Literal["core", "expand", "reference"]
    default_visible: bool


class AnalysisAnnotations(BaseModel):
    vocabulary: list[VocabularyAnnotation] = Field(default_factory=list)
    grammar: list[GrammarAnnotation] = Field(default_factory=list)
    difficult_sentences: list[DifficultSentenceAnnotation] = Field(default_factory=list)


class SentenceTranslation(BaseModel):
    sentence_id: str
    translation_zh: str
    style: Literal["natural", "exam", "literal"] = "natural"


class KeyPhraseTranslation(BaseModel):
    phrase: str
    sentence_id: str
    span: TextSpan
    translation_zh: str


class AnalysisTranslations(BaseModel):
    sentence_translations: list[SentenceTranslation] = Field(default_factory=list)
    full_translation_zh: str
    key_phrase_translations: list[KeyPhraseTranslation] = Field(default_factory=list)


class AnalysisWarning(BaseModel):
    code: str
    message_zh: str


class AnalysisMetrics(BaseModel):
    vocabulary_count: int = Field(ge=0)
    grammar_count: int = Field(ge=0)
    difficult_sentence_count: int = Field(ge=0)
    sentence_count: int = Field(ge=0)
    paragraph_count: int = Field(ge=0)


class AnalysisResult(BaseModel):
    schema_version: Literal["0.1.0"] = ANALYSIS_SCHEMA_VERSION
    request: AnalyzeRequestMeta
    status: AnalysisStatus
    article: ArticleStructure
    annotations: AnalysisAnnotations
    translations: AnalysisTranslations
    discourse: None = None
    warnings: list[AnalysisWarning] = Field(default_factory=list)
    metrics: AnalysisMetrics


class SentenceDifficultyAssessment(BaseModel):
    sentence_id: str
    difficulty_score: float = Field(ge=0.0, le=1.0)
    is_difficult: bool


class CoreAgentOutput(BaseModel):
    sentence_difficulties: list[SentenceDifficultyAssessment] = Field(default_factory=list)
    vocabulary: list[VocabularyAnnotation] = Field(default_factory=list)
    grammar: list[GrammarAnnotation] = Field(default_factory=list)
    difficult_sentences: list[DifficultSentenceAnnotation] = Field(default_factory=list)


class TranslationAgentOutput(BaseModel):
    sentence_translations: list[SentenceTranslation] = Field(default_factory=list)
    full_translation_zh: str
    key_phrase_translations: list[KeyPhraseTranslation] = Field(default_factory=list)

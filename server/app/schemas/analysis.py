from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.llm.types import ModelSelection
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


ANALYSIS_SCHEMA_VERSION = "0.1.0"


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    profile_key: str = "general"
    source_type: Literal["user_input", "daily_article", "ocr"] = "user_input"
    request_id: str | None = None
    discourse_enabled: bool = False
    model_selection: ModelSelection | None = None


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


class VocabularyAnnotation(CoreVocabularyAnnotation):
    type: Literal["vocabulary"] = "vocabulary"
    priority: Literal["core", "expand", "reference"]
    default_visible: bool


class GrammarAnnotation(CoreGrammarAnnotation):
    priority: Literal["core", "expand", "reference"]
    default_visible: bool


class DifficultSentenceAnnotation(CoreDifficultSentenceAnnotation):
    priority: Literal["core", "expand", "reference"]
    default_visible: bool


class AnalysisAnnotations(BaseModel):
    vocabulary: list[VocabularyAnnotation] = Field(default_factory=list)
    grammar: list[GrammarAnnotation] = Field(default_factory=list)
    difficult_sentences: list[DifficultSentenceAnnotation] = Field(default_factory=list)


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

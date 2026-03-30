from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.llm.model_selection import ModelSelection

PREPROCESS_SCHEMA_VERSION = "0.1.0"


class IssueSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class QualityGrade(str, Enum):
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class RoutingDecisionType(str, Enum):
    FULL = "full"
    DEGRADED = "degraded"
    REJECT = "reject"


class TextSpan(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class PreprocessRequestMeta(BaseModel):
    request_id: str
    profile_key: str
    source_type: Literal["user_input", "daily_article", "ocr"]


class PreprocessAnalyzeRequest(BaseModel):
    text: str = Field(min_length=1)
    profile_key: str = "general"
    source_type: Literal["user_input", "daily_article", "ocr"] = "user_input"
    request_id: str | None = None
    model_selection: ModelSelection | None = None


class NormalizedText(BaseModel):
    source_text: str
    clean_text: str
    text_changed: bool
    normalization_actions: list[str] = Field(default_factory=list)


class SegmentedParagraph(BaseModel):
    paragraph_id: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class SegmentedSentence(BaseModel):
    sentence_id: str
    paragraph_id: str
    text: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)


class SegmentationResult(BaseModel):
    paragraph_count: int = Field(ge=0)
    sentence_count: int = Field(ge=0)
    paragraphs: list[SegmentedParagraph] = Field(default_factory=list)
    sentences: list[SegmentedSentence] = Field(default_factory=list)


class LanguageDetection(BaseModel):
    primary_language: str
    english_ratio: float = Field(ge=0.0, le=1.0)
    non_english_ratio: float = Field(ge=0.0, le=1.0)


class TextTypeDetection(BaseModel):
    predicted_type: Literal["article", "list", "subtitle", "code", "email", "other"]
    confidence: float = Field(ge=0.0, le=1.0)


class NoiseDetection(BaseModel):
    noise_ratio: float = Field(ge=0.0, le=1.0)
    has_html: bool
    has_code_like_content: bool
    appears_truncated: bool


class DetectionResult(BaseModel):
    language: LanguageDetection
    text_type: TextTypeDetection
    noise: NoiseDetection


class PreprocessIssue(BaseModel):
    issue_id: str
    type: Literal[
        "possible_grammar_issue",
        "possible_spelling_issue",
        "non_english_content",
        "noise_content",
        "truncated_text",
        "unsupported_text_type",
    ]
    severity: IssueSeverity
    sentence_id: str | None = None
    span: TextSpan | None = None
    description_zh: str
    suggestion_zh: str | None = None


class GuardrailsIssue(BaseModel):
    type: Literal[
        "possible_grammar_issue",
        "possible_spelling_issue",
        "non_english_content",
        "noise_content",
        "truncated_text",
        "unsupported_text_type",
    ]
    severity: IssueSeverity
    description_zh: str
    suggestion_zh: str | None = None


class QualityAssessment(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    grade: QualityGrade
    suitable_for_full_annotation: bool
    summary_zh: str


class RoutingDecision(BaseModel):
    decision: RoutingDecisionType
    should_continue: bool
    degrade_reason: str | None = None
    reject_reason: str | None = None


class PreprocessWarning(BaseModel):
    code: str
    message_zh: str


class GuardrailsAssessment(BaseModel):
    text_type: Literal["article", "list", "subtitle", "code", "email", "other"]
    issues: list[GuardrailsIssue] = Field(default_factory=list)
    quality: QualityAssessment
    routing: RoutingDecision
    warnings: list[PreprocessWarning] = Field(default_factory=list)


class PreprocessResult(BaseModel):
    schema_version: Literal["0.1.0"] = PREPROCESS_SCHEMA_VERSION
    request: PreprocessRequestMeta
    normalized: NormalizedText
    segmentation: SegmentationResult
    detection: DetectionResult
    issues: list[PreprocessIssue] = Field(default_factory=list)
    quality: QualityAssessment
    routing: RoutingDecision
    warnings: list[PreprocessWarning] = Field(default_factory=list)

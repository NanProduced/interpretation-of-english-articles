"""Daily Reader internal schemas for agent outputs and workflow state."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DailyVocabHighlight(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    anchor: str = Field(description="The exact text from the original paragraph")
    start: int = Field(description="0-based start index in paragraph text")
    end: int = Field(description="0-based end index in paragraph text")
    type: str = Field(description="vocab_highlight, phrase_gloss, or context_gloss")
    gloss: str = Field(description="Chinese gloss/translation")


class DailyParagraphDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    paragraph_id: str = Field(description="Paragraph ID like p_0, p_1")
    text: str = Field(description="Paragraph text (normalized)")
    highlights: list[DailyVocabHighlight] = Field(default_factory=list)


class DailyVocabDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    paragraphs: list[DailyParagraphDraft] = Field(default_factory=list)


class DailyHighlightDetail(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: str = Field(description="Highlight ID like hl_001")
    type: str = Field(description="vocab_highlight, phrase_gloss, or context_gloss")
    text: str = Field(description="Highlighted text")
    gloss: str = Field(description="Chinese gloss")
    paragraph_id: str = Field(description="Paragraph ID")
    start: int = Field(description="0-based start index")
    end: int = Field(description="0-based end index")
    detail: dict | None = Field(default=None, description="Extra detail: phonetic, pos, context_explanation")


class DailyHighlightsDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    highlights: list[DailyHighlightDetail] = Field(default_factory=list)


class StructurePart(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    label: str
    title: str
    summary: str


class KeyExpression(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    expression: str
    gloss: str
    context_sentence: str


class MisreadingPoint(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    point: str
    clarification: str


class DailyFooterDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    summary: str = Field(description="One-sentence summary in Chinese")
    thesis_and_intent: dict = Field(
        description="Contains 'thesis' and 'author_intent' keys"
    )
    structure: list[StructurePart] = Field(default_factory=list)
    key_expressions: list[KeyExpression] = Field(default_factory=list)
    misreading_points: list[MisreadingPoint] = Field(default_factory=list)
    discussion_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_json_strings(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        for key in ("structure", "key_expressions", "misreading_points", "discussion_questions", "thesis_and_intent"):
            val = data.get(key)
            if isinstance(val, str):
                try:
                    data[key] = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    if key == "thesis_and_intent":
                        data[key] = {}
                    else:
                        data[key] = []
        return data


class DailyInterpretationDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    full_article_analysis: str = Field(description="Full article interpretation text")


class QualityIssue(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    dimension: str
    severity: str = Field(description="minor or major")
    description: str
    suggestion: str


class DailyReviewDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    passed: bool
    overall_score: float
    issues: list[QualityIssue] = Field(default_factory=list)


class DailyRefinementDraft(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    abort: bool = False
    refined_highlights: list[DailyHighlightDetail] | None = None
    refined_footer: DailyFooterDraft | None = None
    refined_interpretation: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_json_strings(cls, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        highlights = data.get("refined_highlights")
        if isinstance(highlights, str):
            try:
                data["refined_highlights"] = json.loads(highlights)
            except (json.JSONDecodeError, ValueError):
                data["refined_highlights"] = None
        footer = data.get("refined_footer")
        if isinstance(footer, str):
            try:
                data["refined_footer"] = json.loads(footer)
            except (json.JSONDecodeError, ValueError):
                data["refined_footer"] = None
        return data

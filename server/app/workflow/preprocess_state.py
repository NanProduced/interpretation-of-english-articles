from __future__ import annotations

from typing import TypedDict

from app.schemas.preprocess import (
    DetectionResult,
    GuardrailsAssessment,
    NormalizedText,
    PreprocessAnalyzeRequest,
    PreprocessResult,
    SegmentationResult,
)


class PreprocessState(TypedDict, total=False):
    """preprocess workflow 的共享状态。"""

    payload: PreprocessAnalyzeRequest
    request_id: str
    normalized: NormalizedText
    segmentation: SegmentationResult
    detection: DetectionResult
    assessment: GuardrailsAssessment
    result: PreprocessResult

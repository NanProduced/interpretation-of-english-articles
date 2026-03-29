from __future__ import annotations

from typing import Literal, TypedDict

from app.schemas.analysis import (
    AnalysisResult,
    AnalysisStatus,
    AnalysisWarning,
    AnalyzeRequest,
    CoreAgentOutput,
    TranslationAgentOutput,
)
from app.schemas.preprocess import PreprocessResult


class AnalyzeState(TypedDict, total=False):
    """analyze workflow 的共享状态。"""

    payload: AnalyzeRequest
    preprocess: PreprocessResult
    route_decision: Literal["continue", "reject"]
    core_output: CoreAgentOutput
    translation_output: TranslationAgentOutput
    warnings: list[AnalysisWarning]
    status: AnalysisStatus
    merged_result: AnalysisResult
    result: AnalysisResult

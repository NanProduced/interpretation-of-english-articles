from __future__ import annotations

from typing import Any, TypedDict

from app.schemas.analysis import AnalyzeRequest, RenderSceneModel
from app.schemas.internal.analysis import PreparedInput, TeachingOutput, UserRules


class AnalyzeState(TypedDict, total=False):
    """article_analysis workflow 的共享状态。"""

    payload: AnalyzeRequest
    prepared_input: PreparedInput
    user_rules: UserRules
    teaching_output: TeachingOutput
    warnings: list[dict[str, Any]]
    result: RenderSceneModel

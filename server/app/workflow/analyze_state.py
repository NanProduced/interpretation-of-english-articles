from __future__ import annotations

from typing import TypedDict

from app.schemas.analysis import AnalyzeRequest, RenderSceneModel, Warning
from app.schemas.internal.analysis import AnnotationOutput, PreparedInput, UserRules


class AnalyzeState(TypedDict, total=False):
    payload: AnalyzeRequest
    prepared_input: PreparedInput
    user_rules: UserRules
    annotation_output: AnnotationOutput
    annotation_usage: dict[str, object]
    warnings: list[Warning]
    result: RenderSceneModel

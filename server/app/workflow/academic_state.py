from __future__ import annotations

from typing import TypedDict

from app.schemas.analysis import AnalyzeRequest, Warning
from app.schemas.internal.analysis import AcademicAnnotationOutput, PreparedInput
from app.schemas.internal.academic_drafts import (
    InterpretationDraft,
    LogicDraft,
    StructureDraft,
    TermDraft,
    AcademicTranslationDraft,
)
from app.schemas.internal.execution_plan import GoalExecutionPlan


class AcademicState(TypedDict, total=False):
    payload: AnalyzeRequest
    prepared_input: PreparedInput
    goal_execution_plan: GoalExecutionPlan

    term_draft: TermDraft | None
    logic_draft: LogicDraft | None
    interpretation_draft: InterpretationDraft | None
    structure_draft: StructureDraft | None
    translation_draft: AcademicTranslationDraft | None

    term_usage: dict[str, object] | None
    logic_usage: dict[str, object] | None
    interpretation_usage: dict[str, object] | None
    structure_usage: dict[str, object] | None
    translation_usage: dict[str, object] | None
    usage_summary: dict[str, object] | None

    academic_output: AcademicAnnotationOutput | None

    render_scene: dict[str, object]

    warnings: list[Warning]
    parallel_agent_errors: list[Warning]
    structure_agent_errors: list[Warning]
    translation_agent_errors: list[Warning]

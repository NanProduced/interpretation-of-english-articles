from __future__ import annotations

from typing import TypedDict

from app.schemas.analysis import AnalyzeRequest, RenderSceneModel, Warning
from app.schemas.internal.analysis import PreparedInput, UserRules
from app.schemas.internal.drafts import GrammarDraft, TranslationDraft, VocabularyDraft
from app.schemas.internal.normalized import DropLogEntry, NormalizedAnnotationResult


class AnalyzeState(TypedDict, total=False):
    # Request & Input
    payload: AnalyzeRequest
    prepared_input: PreparedInput
    user_rules: UserRules

    # V3: Parallel agent drafts
    vocabulary_draft: VocabularyDraft | None
    grammar_draft: GrammarDraft | None
    translation_draft: TranslationDraft | None

    # V3: Normalization result
    normalized_result: NormalizedAnnotationResult | None
    drop_log: list[DropLogEntry]  # Alias for normalized_result.drop_log for direct access

    # V3: Optional repair
    repair_request: dict | None

    # V3: Final result
    render_scene: RenderSceneModel

    # Legacy aliases for compatibility during transition
    annotation_output: dict | None  # Deprecated: use normalized_result
    warnings: list[Warning]
    processing_warnings: list[Warning]  # V3: consolidated warnings

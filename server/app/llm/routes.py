from __future__ import annotations

from typing import Literal

MODEL_ROUTE_PREPROCESS_GUARDRAILS = "preprocess_guardrails"
MODEL_ROUTE_ANALYSIS_CORE = "analysis_core"
MODEL_ROUTE_ANALYSIS_TRANSLATION = "analysis_translation"

ModelRoute = Literal[
    "preprocess_guardrails",
    "analysis_core",
    "analysis_translation",
]

ALL_MODEL_ROUTES: tuple[ModelRoute, ...] = (
    MODEL_ROUTE_PREPROCESS_GUARDRAILS,
    MODEL_ROUTE_ANALYSIS_CORE,
    MODEL_ROUTE_ANALYSIS_TRANSLATION,
)


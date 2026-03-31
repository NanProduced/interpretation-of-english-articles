from __future__ import annotations

from typing import Final, Literal

ModelRoute = Literal[
    "annotation_generation",
]

MODEL_ROUTE_ANNOTATION_GENERATION: Final[ModelRoute] = "annotation_generation"

ALL_MODEL_ROUTES: tuple[ModelRoute, ...] = (
    MODEL_ROUTE_ANNOTATION_GENERATION,
)

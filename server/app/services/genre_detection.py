from __future__ import annotations

import time
from dataclasses import dataclass
from logging import getLogger

from pydantic import BaseModel
from pydantic_ai import Agent

from app.config.settings import get_settings
from app.llm.router import build_model_for_route
from app.llm.routes import MODEL_ROUTE_ANNOTATION_GENERATION
from app.schemas.genre_detection import (
    GenreCategory,
    GenreDetectionRequest,
    GenreDetectionResponse,
    GenreDetectionResult,
)

logger = getLogger(__name__)


_GENRE_DETECTION_INSTRUCTIONS = """
You are a text genre classifier specialized in analyzing English text to determine if it belongs to academic/professional literature.

## Classification Categories

### "academic" (Academic/Professional Literature)
Text should be classified as "academic" if it exhibits MOST of these characteristics:
- Contains formal academic vocabulary (methodology, hypothesis, framework, empirical, paradigm, etc.)
- Uses passive voice frequently ("was analyzed", "were measured", "it has been shown")
- Contains noun-heavy constructions ("the measurement of", "the significance of", "an investigation into")
- Includes hedging language ("suggests", "indicates", "may", "could", "implies", "appears to")
- Has citation markers ([1], (Smith et al., 2023), etc.)
- References IMRAD-like structure (Abstract, Introduction, Method, Results, Discussion)
- Uses technical domain-specific terminology
- Sentences are typically longer and more complex

### "daily" (Daily Reading / General Prose)
Text should be classified as "daily" if it:
- Uses conversational or journalistic language
- Contains simple sentence structures
- Uses active voice predominantly
- Does not contain academic jargon or citation markers
- Is narrative, descriptive, or persuasive in a non-academic way

### "exam_oriented" (Exam Preparation Material)
Text should be classified as "exam_oriented" if it:
- Contains language typical of English exams (CET, IELTS, TOEFL, Gaokao)
- May include comprehension-style passages
- Has structured exercises or question-like elements

### "uncertain"
Use "uncertain" only when the text is too short, too ambiguous, or lacks clear genre signals.

## Output Requirements
Provide:
1. `genre`: The primary classification
2. `confidence`: A float between 0.0 and 1.0 indicating your confidence
3. `reasoning`: A brief explanation of why you classified it this way
4. `signals`: A list of specific features you observed (e.g., ["citation markers", "technical vocabulary", "passive voice"])
5. `suggested_goal`: Suggest "academic" if genre is "academic", otherwise suggest "daily_reading" or "exam" as appropriate. If uncertain, suggest None.

## Important Notes
- Be conservative: only classify as "academic" if there are MULTIPLE clear academic signals
- A single academic word is NOT enough; look for patterns
- Consider the overall tone and purpose of the text
- If the text is clearly NOT academic but you see one academic word, do NOT classify as "academic"
"""


class _GenreDetectionOutput(BaseModel):
    genre: GenreCategory
    confidence: float
    reasoning: str
    signals: list[str]
    suggested_goal: str | None


@dataclass
class _GenreDetectionDeps:
    text: str


def _build_genre_detection_prompt(deps: _GenreDetectionDeps) -> str:
    return f"""Analyze the following English text and classify its genre:

=== TEXT START ===
{deps.text}
=== TEXT END ===

Classify this text into one of: academic, daily, exam_oriented, uncertain.

Provide your reasoning and list specific signals you observe."""


def _get_genre_detection_agent() -> Agent[_GenreDetectionDeps, _GenreDetectionOutput]:
    return Agent[_GenreDetectionDeps, _GenreDetectionOutput](
        model=None,
        output_type=_GenreDetectionOutput,
        deps_type=_GenreDetectionDeps,
        instructions=_GENRE_DETECTION_INSTRUCTIONS,
        name="genre_detection_agent",
        retries=1,
        output_retries=2,
        instrument=False,
    )


async def detect_text_genre(
    request: GenreDetectionRequest,
) -> GenreDetectionResponse:
    start_time = time.perf_counter()

    settings = get_settings()

    model, model_config = build_model_for_route(
        settings,
        MODEL_ROUTE_ANNOTATION_GENERATION,
        model_selection=None,
    )

    if model is None:
        logger.warning("No model configured for genre detection, returning default result")
        return GenreDetectionResponse(
            detection=GenreDetectionResult(
                genre="uncertain",
                confidence=0.0,
                suggested_goal=None,
                reasoning="Model not configured for detection",
                signals=[],
            ),
            latency_ms=0,
        )

    agent = _get_genre_detection_agent()
    deps = _GenreDetectionDeps(text=request.text)
    prompt = _build_genre_detection_prompt(deps)

    try:
        result = await agent.run(
            prompt,
            deps=deps,
            model=model,
        )

        output = result.output if hasattr(result, "output") else result
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        suggested_goal: str | None = None
        if output.genre == "academic":
            suggested_goal = "academic"
        elif output.genre == "exam_oriented":
            suggested_goal = "exam"
        elif output.genre == "daily":
            suggested_goal = "daily_reading"

        detection = GenreDetectionResult(
            genre=output.genre,
            confidence=output.confidence,
            suggested_goal=suggested_goal,
            reasoning=output.reasoning,
            signals=output.signals,
        )

        logger.info(
            "Genre detection complete: genre=%s, confidence=%.2f, signals=%s, latency=%dms",
            detection.genre,
            detection.confidence,
            detection.signals,
            latency_ms,
        )

        return GenreDetectionResponse(
            detection=detection,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error("Genre detection failed: %s", e, exc_info=True)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return GenreDetectionResponse(
            detection=GenreDetectionResult(
                genre="uncertain",
                confidence=0.0,
                suggested_goal=None,
                reasoning=f"Detection error: {str(e)}",
                signals=[],
            ),
            latency_ms=latency_ms,
        )

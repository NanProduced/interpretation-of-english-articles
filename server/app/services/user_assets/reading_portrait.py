"""
Reading Portrait Service.

Handles reading portrait generation and management:
- Extracts signals from analysis records
- Accumulates signals to user profile summary
- Generates user-readable portrait using LLM when conditions met
"""

from __future__ import annotations

import json
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.database import connection as db_connection
from app.llm.router import build_model_for_route
from app.llm.routes import MODEL_ROUTE_DAILY_ANALYSIS

logger = logging.getLogger(__name__)

PORTRAIT_GENERATION_THRESHOLD = 5
PORTRAIT_GENERATION_HOURS = 24
MAX_RECENT_SIGNALS = 10


class ReadingSignal:
    """Structured reading signal extracted from analysis record."""

    __slots__ = (
        "reading_goal",
        "reading_variant",
        "word_count",
        "schema_version",
        "is_academic",
        "annotation_count",
        "record_id",
        "created_at",
    )

    def __init__(
        self,
        reading_goal: str,
        reading_variant: str,
        word_count: int,
        schema_version: str,
        is_academic: bool,
        annotation_count: int,
        record_id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.reading_goal = reading_goal
        self.reading_variant = reading_variant
        self.word_count = word_count
        self.schema_version = schema_version
        self.is_academic = is_academic
        self.annotation_count = annotation_count
        self.record_id = record_id
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reading_goal": self.reading_goal,
            "reading_variant": self.reading_variant,
            "word_count": self.word_count,
            "schema_version": self.schema_version,
            "is_academic": self.is_academic,
            "annotation_count": self.annotation_count,
            "record_id": str(self.record_id) if self.record_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReadingSignal:
        record_id = UUID(data["record_id"]) if data.get("record_id") else None
        created_at = (
            datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None
        )
        return cls(
            reading_goal=data["reading_goal"],
            reading_variant=data["reading_variant"],
            word_count=data["word_count"],
            schema_version=data["schema_version"],
            is_academic=data["is_academic"],
            annotation_count=data["annotation_count"],
            record_id=record_id,
            created_at=created_at,
        )


def extract_signal_from_record(
    record: dict[str, Any],
    render_scene_json: dict[str, Any] | None = None,
) -> ReadingSignal:
    """
    Extract structured reading signal from analysis record.

    Args:
        record: The analysis record dictionary
        render_scene_json: Optional render scene JSON for annotation count

    Returns:
        ReadingSignal object
    """
    reading_goal = record.get("reading_goal") or "daily_reading"
    reading_variant = record.get("reading_variant") or "intermediate_reading"

    source_text = record.get("source_text") or ""
    word_count = len(source_text.split())

    schema_version = record.get("schema_version") or "3.0.0"
    if render_scene_json:
        schema_version = render_scene_json.get("schema_version") or schema_version

    is_academic = reading_goal == "academic"

    annotation_count = 0
    if render_scene_json:
        inline_marks = render_scene_json.get("inline_marks") or []
        sentence_entries = render_scene_json.get("sentence_entries") or []
        annotation_count = len(inline_marks) + len(sentence_entries)

    record_id = record.get("id")
    if isinstance(record_id, str):
        record_id = UUID(record_id)

    return ReadingSignal(
        reading_goal=reading_goal,
        reading_variant=reading_variant,
        word_count=word_count,
        schema_version=schema_version,
        is_academic=is_academic,
        annotation_count=annotation_count,
        record_id=record_id,
    )


def _ensure_dict(value: Any) -> dict:
    """Ensure value is a dict, parsing JSON if needed."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _increment_count(counts: dict[str, int], key: str, amount: int = 1) -> None:
    """Increment a count in a dictionary."""
    counts[key] = counts.get(key, 0) + amount


def _should_generate_portrait(
    signal_count_since_last: int,
    last_generated_at: datetime | None,
) -> bool:
    """
    Check if portrait should be generated.

    Conditions:
    - Signal count since last generation >= threshold (5)
    - OR (has generated before AND time since last generation > 24 hours AND has new signals)
    """
    if signal_count_since_last >= PORTRAIT_GENERATION_THRESHOLD:
        return True

    if last_generated_at is None:
        return False

    time_since_last = datetime.now(timezone.utc) - last_generated_at
    if time_since_last > timedelta(hours=PORTRAIT_GENERATION_HOURS):
        return signal_count_since_last > 0

    return False


async def _get_or_create_profile(
    conn: Any,
    user_id: UUID,
) -> dict[str, Any]:
    """
    Get or create a reading profile for a user using an existing connection.

    Args:
        conn: Database connection (already acquired)
        user_id: The user UUID

    Returns:
        Reading profile dictionary
    """
    row = await conn.fetchrow(
        """
        INSERT INTO user_reading_profiles (user_id)
        VALUES ($1)
        ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
        RETURNING *
        """,
        user_id,
    )
    if row is None:
        raise RuntimeError("Failed to get or create reading profile")

    profile = dict(row)
    profile["reading_goals_json"] = _ensure_dict(profile.get("reading_goals_json"))
    profile["reading_variants_json"] = _ensure_dict(profile.get("reading_variants_json"))
    profile["schema_versions_json"] = _ensure_dict(profile.get("schema_versions_json"))
    profile["recent_signals_json"] = _ensure_dict(profile.get("recent_signals_json")) or []

    return profile


async def get_or_create_reading_profile(user_id: UUID) -> dict[str, Any]:
    """
    Get or create a reading profile for a user.

    Args:
        user_id: The user UUID

    Returns:
        Reading profile dictionary
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        return await _get_or_create_profile(conn, user_id)


async def _accumulate_signal_internal(
    conn: Any,
    user_id: UUID,
    signal: ReadingSignal,
) -> dict[str, Any]:
    """
    Accumulate a reading signal using an existing connection.

    Args:
        conn: Database connection (already acquired)
        user_id: The user UUID
        signal: The reading signal to accumulate

    Returns:
        Updated reading profile
    """
    profile = await _get_or_create_profile(conn, user_id)

    reading_goals = profile["reading_goals_json"]
    _increment_count(reading_goals, signal.reading_goal)

    reading_variants = profile["reading_variants_json"]
    _increment_count(reading_variants, signal.reading_variant)

    schema_versions = profile["schema_versions_json"]
    _increment_count(schema_versions, signal.schema_version)

    total_word_count = (profile.get("total_word_count") or 0) + signal.word_count
    total_annotation_count = (
        (profile.get("total_annotation_count") or 0) + signal.annotation_count
    )

    academic_count = profile.get("academic_count") or 0
    non_academic_count = profile.get("non_academic_count") or 0
    if signal.is_academic:
        academic_count += 1
    else:
        non_academic_count += 1

    recent_signals: list[dict] = profile["recent_signals_json"] or []
    recent_signals.append(signal.to_dict())
    if len(recent_signals) > MAX_RECENT_SIGNALS:
        recent_signals = recent_signals[-MAX_RECENT_SIGNALS:]

    signal_count_since_last = (
        profile.get("portrait_signal_count_since_last") or 0
    ) + 1

    await conn.execute(
        """
        UPDATE user_reading_profiles
        SET reading_goals_json = $2::jsonb,
            reading_variants_json = $3::jsonb,
            schema_versions_json = $4::jsonb,
            total_word_count = $5,
            total_annotation_count = $6,
            academic_count = $7,
            non_academic_count = $8,
            recent_signals_json = $9::jsonb,
            portrait_signal_count_since_last = $10,
            updated_at = NOW()
        WHERE user_id = $1
        """,
        user_id,
        json.dumps(reading_goals, ensure_ascii=False),
        json.dumps(reading_variants, ensure_ascii=False),
        json.dumps(schema_versions, ensure_ascii=False),
        total_word_count,
        total_annotation_count,
        academic_count,
        non_academic_count,
        json.dumps(recent_signals, ensure_ascii=False),
        signal_count_since_last,
    )

    profile["reading_goals_json"] = reading_goals
    profile["reading_variants_json"] = reading_variants
    profile["schema_versions_json"] = schema_versions
    profile["total_word_count"] = total_word_count
    profile["total_annotation_count"] = total_annotation_count
    profile["academic_count"] = academic_count
    profile["non_academic_count"] = non_academic_count
    profile["recent_signals_json"] = recent_signals
    profile["portrait_signal_count_since_last"] = signal_count_since_last

    return profile


async def accumulate_signal(
    user_id: UUID,
    signal: ReadingSignal,
) -> dict[str, Any]:
    """
    Accumulate a reading signal to the user's profile.

    Args:
        user_id: The user UUID
        signal: The reading signal to accumulate

    Returns:
        Updated reading profile
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        async with conn.transaction():
            return await _accumulate_signal_internal(conn, user_id, signal)


async def generate_portrait_if_needed(
    user_id: UUID,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Generate reading portrait if conditions are met.

    Args:
        user_id: The user UUID
        profile: Optional pre-fetched profile

    Returns:
        Generated portrait data if generated, None otherwise
    """
    if profile is None:
        profile = await get_or_create_reading_profile(user_id)

    signal_count_since_last = profile.get("portrait_signal_count_since_last") or 0
    last_generated_at = profile.get("portrait_generated_at")

    if not _should_generate_portrait(signal_count_since_last, last_generated_at):
        return None

    try:
        portrait_data = await _generate_portrait_with_llm(profile)
        if portrait_data:
            await _save_portrait(user_id, portrait_data)
            return portrait_data
    except Exception as e:
        logger.error("Failed to generate reading portrait: %s", e, exc_info=True)

    return None


async def _generate_portrait_with_llm(
    profile: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Generate reading portrait using LLM.

    Args:
        profile: The user's reading profile

    Returns:
        Generated portrait data, or None if generation failed
    """
    from app.agents.reading_portrait_agent import (
        ReadingPortraitAgentDeps,
        build_reading_portrait_prompt,
        get_reading_portrait_agent,
    )
    from app.config.settings import get_settings

    recent_signals = profile.get("recent_signals_json") or []
    reading_goals = profile.get("reading_goals_json") or {}
    reading_variants = profile.get("reading_variants_json") or {}

    summary_data = {
        "reading_goals": reading_goals,
        "reading_variants": reading_variants,
        "total_word_count": profile.get("total_word_count") or 0,
        "total_annotation_count": profile.get("total_annotation_count") or 0,
        "academic_count": profile.get("academic_count") or 0,
        "non_academic_count": profile.get("non_academic_count") or 0,
        "recent_signals": recent_signals[-5:],
    }

    signals_json = json.dumps(summary_data, ensure_ascii=False, indent=2)

    deps = ReadingPortraitAgentDeps(
        signals_json=signals_json,
        prompt_context={},
    )

    agent = get_reading_portrait_agent()
    prompt = build_reading_portrait_prompt(deps)

    settings = get_settings()
    model, _ = build_model_for_route(settings, MODEL_ROUTE_DAILY_ANALYSIS)
    if model is None:
        logger.warning("No model configured for reading portrait generation")
        return None

    try:
        result = await agent.run(prompt, deps=deps, model=model)
        output = result.output if hasattr(result, "output") else None

        if output is None:
            logger.warning("Agent result has no output attribute")
            return None

        return {
            "common_content": output.common_content,
            "current_challenges": output.current_challenges,
            "next_steps": output.next_steps,
        }
    except Exception as e:
        logger.error("LLM portrait generation failed: %s", e, exc_info=True)
        return None


async def _save_portrait(
    user_id: UUID,
    portrait_data: dict[str, Any],
) -> None:
    """
    Save generated portrait to database.

    Args:
        user_id: The user UUID
        portrait_data: The portrait data to save
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    portrait_text = json.dumps(portrait_data, ensure_ascii=False)

    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE user_reading_profiles
            SET portrait_text = $2,
                portrait_generated_at = NOW(),
                portrait_signal_count_since_last = 0,
                updated_at = NOW()
            WHERE user_id = $1
            """,
            user_id,
            portrait_text,
        )


async def get_reading_portrait(user_id: UUID) -> dict[str, Any] | None:
    """
    Get the user's reading portrait.

    Args:
        user_id: The user UUID

    Returns:
        Portrait data if exists, None otherwise
    """
    pool = db_connection.DB_POOL
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT portrait_text, portrait_generated_at
            FROM user_reading_profiles
            WHERE user_id = $1
            """,
            user_id,
        )

        if row is None:
            return None

        portrait_text = row.get("portrait_text")
        if not portrait_text:
            return None

        try:
            portrait_data = json.loads(portrait_text)
            portrait_data["generated_at"] = (
                row["portrait_generated_at"].isoformat()
                if row.get("portrait_generated_at")
                else None
            )
            return portrait_data
        except (json.JSONDecodeError, TypeError):
            return None


async def process_signal_for_portrait(
    user_id: UUID,
    record: dict[str, Any],
    render_scene_json: dict[str, Any] | None = None,
) -> None:
    """
    Process a reading signal for portrait update.

    This is the main entry point to be called after analysis task success.
    It extracts the signal, accumulates it, and generates portrait if needed.
    FAILURES HERE DO NOT AFFECT THE MAIN FLOW - all exceptions are logged but not raised.

    Args:
        user_id: The user UUID
        record: The analysis record
        render_scene_json: Optional render scene JSON
    """
    try:
        signal = extract_signal_from_record(record, render_scene_json)
        profile = await accumulate_signal(user_id, signal)
        await generate_portrait_if_needed(user_id, profile)
    except Exception as e:
        logger.error(
            "Failed to process signal for portrait (user=%s): %s",
            user_id,
            e,
            exc_info=True,
        )

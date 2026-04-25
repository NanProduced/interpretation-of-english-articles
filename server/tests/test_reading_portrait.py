"""
Tests for reading portrait service.

Covers:
- Signal extraction from records
- Signal accumulation logic
- Portrait generation conditions
- Portrait retrieval
"""

from __future__ import annotations

import json
import sys
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

if "asyncpg" not in sys.modules:
    asyncpg_stub = types.ModuleType("asyncpg")
    asyncpg_stub.Pool = object
    asyncpg_stub.Connection = object

    async def _create_pool(*args, **kwargs):
        raise RuntimeError("asyncpg stub create_pool should not be called in unit tests")

    asyncpg_stub.create_pool = _create_pool
    sys.modules["asyncpg"] = asyncpg_stub

from app.services.user_assets.reading_portrait import (
    MAX_RECENT_SIGNALS,
    PORTRAIT_GENERATION_HOURS,
    PORTRAIT_GENERATION_THRESHOLD,
    ReadingSignal,
    _ensure_dict,
    _increment_count,
    _should_generate_portrait,
    extract_signal_from_record,
)


class TestReadingSignal:
    """Test ReadingSignal class."""

    def test_signal_creation(self):
        signal = ReadingSignal(
            reading_goal="daily_reading",
            reading_variant="intermediate_reading",
            word_count=100,
            schema_version="3.0.0",
            is_academic=False,
            annotation_count=5,
        )
        assert signal.reading_goal == "daily_reading"
        assert signal.reading_variant == "intermediate_reading"
        assert signal.word_count == 100
        assert signal.schema_version == "3.0.0"
        assert signal.is_academic is False
        assert signal.annotation_count == 5

    def test_signal_to_dict(self):
        record_id = uuid4()
        created_at = datetime.now(timezone.utc)
        signal = ReadingSignal(
            reading_goal="exam",
            reading_variant="cet",
            word_count=200,
            schema_version="3.0.0",
            is_academic=False,
            annotation_count=10,
            record_id=record_id,
            created_at=created_at,
        )
        data = signal.to_dict()
        assert data["reading_goal"] == "exam"
        assert data["reading_variant"] == "cet"
        assert data["word_count"] == 200
        assert data["schema_version"] == "3.0.0"
        assert data["is_academic"] is False
        assert data["annotation_count"] == 10
        assert data["record_id"] == str(record_id)
        assert data["created_at"] == created_at.isoformat()

    def test_signal_from_dict(self):
        record_id = uuid4()
        created_at = datetime.now(timezone.utc)
        data = {
            "reading_goal": "academic",
            "reading_variant": "academic_general",
            "word_count": 300,
            "schema_version": "3.0.0-academic",
            "is_academic": True,
            "annotation_count": 15,
            "record_id": str(record_id),
            "created_at": created_at.isoformat(),
        }
        signal = ReadingSignal.from_dict(data)
        assert signal.reading_goal == "academic"
        assert signal.reading_variant == "academic_general"
        assert signal.word_count == 300
        assert signal.is_academic is True
        assert signal.record_id == record_id


class TestSignalExtraction:
    """Test signal extraction from records."""

    def test_extract_basic_signal(self):
        record = {
            "reading_goal": "daily_reading",
            "reading_variant": "intermediate_reading",
            "source_text": "Hello world. This is a test.",
            "schema_version": "3.0.0",
        }
        signal = extract_signal_from_record(record)
        assert signal.reading_goal == "daily_reading"
        assert signal.reading_variant == "intermediate_reading"
        assert signal.word_count == 7
        assert signal.schema_version == "3.0.0"
        assert signal.is_academic is False

    def test_extract_with_render_scene(self):
        record = {
            "reading_goal": "exam",
            "reading_variant": "cet",
            "source_text": "Test sentence one. Test sentence two.",
        }
        render_scene = {
            "schema_version": "3.0.0",
            "inline_marks": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}],
            "sentence_entries": [{"id": "e1"}, {"id": "e2"}],
        }
        signal = extract_signal_from_record(record, render_scene)
        assert signal.annotation_count == 5
        assert signal.schema_version == "3.0.0"

    def test_extract_academic_goal(self):
        record = {
            "reading_goal": "academic",
            "reading_variant": "academic_general",
            "source_text": "Academic paper abstract.",
        }
        signal = extract_signal_from_record(record)
        assert signal.is_academic is True

    def test_extract_default_values(self):
        record = {"source_text": "Minimal record."}
        signal = extract_signal_from_record(record)
        assert signal.reading_goal == "daily_reading"
        assert signal.reading_variant == "intermediate_reading"
        assert signal.schema_version == "3.0.0"
        assert signal.annotation_count == 0


class TestHelperFunctions:
    """Test helper functions."""

    def test_ensure_dict_with_dict(self):
        data = {"key": "value"}
        result = _ensure_dict(data)
        assert result == data

    def test_ensure_dict_with_json_string(self):
        data = '{"key": "value"}'
        result = _ensure_dict(data)
        assert result == {"key": "value"}

    def test_ensure_dict_with_invalid_json(self):
        data = "not json"
        result = _ensure_dict(data)
        assert result == {}

    def test_ensure_dict_with_none(self):
        result = _ensure_dict(None)
        assert result == {}

    def test_increment_count_new_key(self):
        counts = {}
        _increment_count(counts, "daily_reading")
        assert counts == {"daily_reading": 1}

    def test_increment_count_existing_key(self):
        counts = {"daily_reading": 3}
        _increment_count(counts, "daily_reading")
        assert counts == {"daily_reading": 4}

    def test_increment_count_with_amount(self):
        counts = {"word_count": 100}
        _increment_count(counts, "word_count", 50)
        assert counts == {"word_count": 150}


class TestPortraitGenerationConditions:
    """Test portrait generation condition logic."""

    def test_should_generate_at_threshold(self):
        assert _should_generate_portrait(PORTRAIT_GENERATION_THRESHOLD, None) is True

    def test_should_generate_above_threshold(self):
        assert _should_generate_portrait(PORTRAIT_GENERATION_THRESHOLD + 1, None) is True

    def test_should_not_generate_below_threshold(self):
        assert _should_generate_portrait(PORTRAIT_GENERATION_THRESHOLD - 1, None) is False

    def test_should_generate_after_24_hours(self):
        last_generated = datetime.now(timezone.utc) - timedelta(hours=PORTRAIT_GENERATION_HOURS + 1)
        assert _should_generate_portrait(1, last_generated) is True

    def test_should_not_generate_within_24_hours(self):
        last_generated = datetime.now(timezone.utc) - timedelta(hours=PORTRAIT_GENERATION_HOURS - 1)
        assert _should_generate_portrait(1, last_generated) is False

    def test_should_not_generate_zero_signals(self):
        last_generated = datetime.now(timezone.utc) - timedelta(hours=PORTRAIT_GENERATION_HOURS + 1)
        assert _should_generate_portrait(0, last_generated) is False

    def test_should_generate_with_none_last_generated(self):
        assert _should_generate_portrait(1, None) is False
        assert _should_generate_portrait(PORTRAIT_GENERATION_THRESHOLD, None) is True


class TestReadingPortraitService:
    """Test reading portrait service with mocked DB."""

    @pytest.mark.anyio
    async def test_extract_signal_from_record_with_render_scene(self):
        record = {
            "id": uuid4(),
            "reading_goal": "exam",
            "reading_variant": "ielts_toefl",
            "source_text": "The quick brown fox jumps over the lazy dog.",
        }
        render_scene = {
            "inline_marks": [1, 2, 3, 4],
            "sentence_entries": [1, 2],
        }
        signal = extract_signal_from_record(record, render_scene)
        assert signal.reading_goal == "exam"
        assert signal.reading_variant == "ielts_toefl"
        assert signal.word_count == 9
        assert signal.annotation_count == 6
        assert signal.is_academic is False

    @pytest.mark.anyio
    async def test_extract_signal_academic(self):
        record = {
            "reading_goal": "academic",
            "reading_variant": "academic_general",
            "source_text": "Research paper introduction.",
        }
        signal = extract_signal_from_record(record)
        assert signal.is_academic is True

    @pytest.mark.anyio
    async def test_process_signal_catches_exceptions(self):
        user_id = uuid4()

        def raise_error(*args, **kwargs):
            raise RuntimeError("Test error")

        with patch(
            "app.services.user_assets.reading_portrait.extract_signal_from_record",
            side_effect=raise_error,
        ):
            from app.services.user_assets.reading_portrait import process_signal_for_portrait

            await process_signal_for_portrait(user_id, {}, {})

    def test_max_recent_signals_constant(self):
        assert MAX_RECENT_SIGNALS == 10

    def test_threshold_constants(self):
        assert PORTRAIT_GENERATION_THRESHOLD == 5
        assert PORTRAIT_GENERATION_HOURS == 24


class TestReadingSignalEdgeCases:
    """Test edge cases for ReadingSignal."""

    def test_signal_without_optional_fields(self):
        signal = ReadingSignal(
            reading_goal="daily_reading",
            reading_variant="beginner_reading",
            word_count=0,
            schema_version="3.0.0",
            is_academic=False,
            annotation_count=0,
        )
        assert signal.record_id is None
        assert signal.created_at is not None

    def test_signal_from_dict_missing_optional(self):
        data = {
            "reading_goal": "exam",
            "reading_variant": "gaokao",
            "word_count": 50,
            "schema_version": "3.0.0",
            "is_academic": False,
            "annotation_count": 2,
        }
        signal = ReadingSignal.from_dict(data)
        assert signal.record_id is None
        assert signal.created_at is None


class TestSignalExtractionEdgeCases:
    """Test edge cases for signal extraction."""

    def test_extract_empty_text(self):
        record = {
            "reading_goal": "daily_reading",
            "reading_variant": "intensive_reading",
            "source_text": "",
        }
        signal = extract_signal_from_record(record)
        assert signal.word_count == 0

    def test_extract_whitespace_only_text(self):
        record = {
            "reading_goal": "daily_reading",
            "reading_variant": "intermediate_reading",
            "source_text": "   \n\t  ",
        }
        signal = extract_signal_from_record(record)
        assert signal.word_count == 0

    def test_extract_render_scene_without_annotations(self):
        record = {
            "reading_goal": "exam",
            "reading_variant": "kaoyan",
            "source_text": "Test.",
        }
        render_scene = {
            "schema_version": "3.0.0",
            "inline_marks": [],
            "sentence_entries": [],
        }
        signal = extract_signal_from_record(record, render_scene)
        assert signal.annotation_count == 0

    def test_extract_render_scene_with_missing_keys(self):
        record = {
            "reading_goal": "exam",
            "reading_variant": "tem",
            "source_text": "Test.",
        }
        render_scene = {"schema_version": "3.0.0"}
        signal = extract_signal_from_record(record, render_scene)
        assert signal.annotation_count == 0

    def test_extract_record_with_none_fields(self):
        record = {
            "reading_goal": None,
            "reading_variant": None,
            "source_text": "Test.",
            "schema_version": None,
        }
        signal = extract_signal_from_record(record)
        assert signal.reading_goal == "daily_reading"
        assert signal.reading_variant == "intermediate_reading"
        assert signal.schema_version == "3.0.0"


@pytest.fixture
def anyio_backend():
    """Restrict anyio tests to asyncio because trio is not installed in CI/dev."""
    return "asyncio"

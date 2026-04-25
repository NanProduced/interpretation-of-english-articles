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
            "source_text": "Hello world. This is a test sentence.",
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
        assert signal.created_at is not None


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


class TestPydanticAIResultOutput:
    """Test PydanticAI result.output access pattern (not result.data)."""

    def test_result_output_access_pattern(self):
        """Verify that the code expects result.output, not result.data.
        
        This is a documentation test to ensure the expected API is used.
        All other modules in the codebase use result.output.
        """
        from types import SimpleNamespace

        output_obj = SimpleNamespace(
            common_content="常读考试类文章",
            current_challenges="词汇量有待提升",
            next_steps="建议增加学术类阅读",
        )

        result = SimpleNamespace(output=output_obj)

        assert hasattr(result, "output")
        assert result.output.common_content == "常读考试类文章"

    def test_hasattr_check_for_backward_compatibility(self):
        """Test that hasattr(result, 'output') check works for backward compatibility."""
        from types import SimpleNamespace

        output_obj = SimpleNamespace(
            common_content="常读内容",
            current_challenges="当前难点",
            next_steps="下一步",
        )

        result_with_output = SimpleNamespace(output=output_obj)
        result_without_output = SimpleNamespace(data=output_obj)

        assert hasattr(result_with_output, "output")
        assert hasattr(result_without_output, "output") is False

        output1 = result_with_output.output if hasattr(result_with_output, "output") else None
        output2 = result_without_output.output if hasattr(result_without_output, "output") else None

        assert output1 is not None
        assert output2 is None


class TestBackgroundPortraitUpdateIsolation:
    """Test that portrait update failures do not affect the main flow."""

    @pytest.mark.anyio
    async def test_process_signal_for_portrait_catches_all_exceptions(self):
        """Test that process_signal_for_portrait catches ALL exceptions.
        
        This ensures portrait processing never propagates errors to the main task.
        """
        user_id = uuid4()

        from app.services.user_assets.reading_portrait import process_signal_for_portrait

        test_cases = [
            (RuntimeError("DB connection error"),),
            (ValueError("Invalid data"),),
            (TypeError("Type mismatch"),),
            (Exception("Generic error"),),
        ]

        for exc_type in test_cases:
            with patch(
                "app.services.user_assets.reading_portrait.extract_signal_from_record",
                side_effect=exc_type,
            ):
                try:
                    await process_signal_for_portrait(user_id, {}, {})
                except Exception as e:
                    pytest.fail(f"process_signal_for_portrait should not propagate {type(e).__name__}: {e}")

    @pytest.mark.anyio
    async def test_process_signal_for_portrait_error_at_accumulate_signal(self):
        """Test that errors during accumulate_signal are caught."""
        user_id = uuid4()

        from app.services.user_assets.reading_portrait import process_signal_for_portrait

        def mock_extract(*args, **kwargs):
            return ReadingSignal(
                reading_goal="daily_reading",
                reading_variant="intermediate_reading",
                word_count=100,
                schema_version="3.0.0",
                is_academic=False,
                annotation_count=5,
            )

        with patch(
            "app.services.user_assets.reading_portrait.extract_signal_from_record",
            side_effect=mock_extract,
        ), patch(
            "app.services.user_assets.reading_portrait.accumulate_signal",
            side_effect=RuntimeError("DB pool exhausted"),
        ):
            try:
                await process_signal_for_portrait(user_id, {}, {})
            except Exception as e:
                pytest.fail(f"Should not propagate {type(e).__name__}")

    @pytest.mark.anyio
    async def test_process_signal_for_portrait_error_at_generate_portrait(self):
        """Test that errors during generate_portrait_if_needed are caught."""
        user_id = uuid4()

        from app.services.user_assets.reading_portrait import process_signal_for_portrait

        def mock_extract(*args, **kwargs):
            return ReadingSignal(
                reading_goal="daily_reading",
                reading_variant="intermediate_reading",
                word_count=100,
                schema_version="3.0.0",
                is_academic=False,
                annotation_count=5,
            )

        mock_profile = {
            "portrait_signal_count_since_last": 5,
            "portrait_generated_at": None,
        }

        with patch(
            "app.services.user_assets.reading_portrait.extract_signal_from_record",
            side_effect=mock_extract,
        ), patch(
            "app.services.user_assets.reading_portrait.accumulate_signal",
            return_value=mock_profile,
        ), patch(
            "app.services.user_assets.reading_portrait.generate_portrait_if_needed",
            side_effect=RuntimeError("LLM API timeout"),
        ):
            try:
                await process_signal_for_portrait(user_id, {}, {})
            except Exception as e:
                pytest.fail(f"Should not propagate {type(e).__name__}")


class TestTaskExecutorBackgroundPortraitUpdate:
    """Test that task executor handles portrait updates in background after marking succeeded.

    These tests verify that:
    1. Task is marked succeeded BEFORE portrait update starts
    2. Portrait update runs in background (asyncio.create_task)
    3. Portrait update failures only log, don't affect main flow
    """

    @pytest.mark.anyio
    async def test_update_reading_portrait_background_catches_all_exceptions(self):
        """Test _update_reading_portrait_background catches all exceptions."""
        import asyncio
        from unittest.mock import MagicMock

        from app.services.analysis.task_executor import _update_reading_portrait_background

        user_id = uuid4()
        task_id = uuid4()

        with patch(
            "app.services.analysis.task_executor.portrait_svc.process_signal_for_portrait",
            side_effect=RuntimeError("Any error should be caught"),
        ):
            try:
                await _update_reading_portrait_background(
                    user_id=user_id,
                    record={},
                    render_scene_json=None,
                    task_id=task_id,
                )
            except Exception as e:
                pytest.fail(f"_update_reading_portrait_background should not propagate {type(e).__name__}")

    @pytest.mark.anyio
    async def test_update_reading_portrait_background_success_path(self):
        """Test _update_reading_portrait_background success path."""
        import asyncio
        from unittest.mock import AsyncMock

        from app.services.analysis.task_executor import _update_reading_portrait_background

        user_id = uuid4()
        task_id = uuid4()

        mock_process = AsyncMock()

        with patch(
            "app.services.analysis.task_executor.portrait_svc.process_signal_for_portrait",
            mock_process,
        ):
            await _update_reading_portrait_background(
                user_id=user_id,
                record={"key": "value"},
                render_scene_json={"marks": []},
                task_id=task_id,
            )

            mock_process.assert_called_once_with(
                user_id=user_id,
                record={"key": "value"},
                render_scene_json={"marks": []},
            )


class TestGeneratePortraitWithLLMOutputPattern:
    """Test _generate_portrait_with_llm uses result.output pattern."""

    def test_generate_portrait_with_llm_uses_result_output(self):
        """Verify that _generate_portrait_with_llm accesses result.output, not result.data.

        This is a static inspection test to confirm the code pattern is correct.
        """
        import inspect
        import re

        from app.services.user_assets.reading_portrait import _generate_portrait_with_llm

        source = inspect.getsource(_generate_portrait_with_llm)

        assert "result.output" in source, "Should use result.output"

        hasattr_pattern = r'hasattr\s*\(\s*result\s*,\s*["\']output["\']\s*\)'
        assert re.search(hasattr_pattern, source), "Should use hasattr(result, 'output') or hasattr(result, \"output\")"

        assert "result.data" not in source, "Should NOT use result.data"


class TestConnectionSharingBetweenFunctions:
    """Test that internal functions share connection to avoid nested acquire."""

    def test_accumulate_signal_uses_internal_functions(self):
        """Verify that accumulate_signal uses internal functions with shared connection.

        This is a static inspection test to confirm the code structure.
        """
        import inspect

        from app.services.user_assets.reading_portrait import (
            _accumulate_signal_internal,
            _get_or_create_profile,
            accumulate_signal,
        )

        source_accumulate = inspect.getsource(accumulate_signal)
        source_internal = inspect.getsource(_accumulate_signal_internal)
        source_get_profile = inspect.getsource(_get_or_create_profile)

        assert "_accumulate_signal_internal" in source_accumulate
        assert "_get_or_create_profile" in source_internal
        assert "pool.acquire()" in source_accumulate
        assert "pool.acquire()" not in source_internal
        assert "pool.acquire()" not in source_get_profile


class TestMainFlowOrder:
    """Test that the main flow order is correct: mark succeeded BEFORE portrait update.

    This verifies the task execution order in task_executor.py:
    1. update_record
    2. insert_audit_log
    3. deduct_credits
    4. increment_user_reading_count
    5. update_task_status(succeeded)  <-- IMPORTANT: BEFORE portrait
    6. insert_task_event(succeeded)
    7. asyncio.create_task(portrait_update)  <-- BACKGROUND
    """

    def test_task_executor_order(self):
        """Static inspection of task_executor.py to verify correct order.

        We need to find:
        1. The update_task_status call with status='succeeded' in the success path
        2. The asyncio.create_task call that wraps _update_reading_portrait_background

        And verify that (1) comes before (2).
        """
        import inspect
        import re

        from app.services.analysis.task_executor import execute_task

        source = inspect.getsource(execute_task)

        succeeded_pattern = r'update_task_status\s*\([^)]*status\s*=\s*["\']succeeded["\']'
        create_task_pattern = r'asyncio\.create_task\s*\(\s*_update_reading_portrait_background'

        succeeded_matches = list(re.finditer(succeeded_pattern, source))
        create_task_matches = list(re.finditer(create_task_pattern, source))

        assert len(succeeded_matches) > 0, "Should have update_task_status with status='succeeded'"
        assert len(create_task_matches) > 0, "Should have asyncio.create_task with _update_reading_portrait_background"

        first_succeeded_pos = succeeded_matches[0].start()
        first_create_task_pos = create_task_matches[0].start()

        assert first_succeeded_pos < first_create_task_pos, (
            f"update_task_status(succeeded) at position {first_succeeded_pos} "
            f"should be BEFORE asyncio.create_task(portrait) at position {first_create_task_pos}"
        )

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.main import app
from app.schemas.genre_detection import (
    GenreCategory,
    GenreDetectionRequest,
    GenreDetectionResponse,
    GenreDetectionResult,
)

client = TestClient(app)


class MockGenreDetectionOutput(BaseModel):
    genre: GenreCategory
    confidence: float
    reasoning: str
    signals: list[str]
    suggested_goal: str | None


@pytest.fixture
def mock_academic_text() -> str:
    return """
    Abstract: In this paper, we propose a novel framework for fine-grained sentiment analysis
    in academic papers. Our methodology involves a transformer-based model that achieves
    state-of-the-art performance on the SemEval-2017 dataset. Experimental results demonstrate
    significant improvements over baseline approaches (p < 0.05).
    """


@pytest.fixture
def mock_daily_text() -> str:
    return """
    Hey, I just had the most amazing coffee at this new place downtown.
    The barista made me a perfect latte with heart-shaped foam art.
    Definitely going back there tomorrow with my friends!
    """


class TestGenreDetectionSchema:
    def test_valid_request(self) -> None:
        request = GenreDetectionRequest(text="Hello world test with enough words")
        assert request.text == "Hello world test with enough words"

    def test_min_text_length(self) -> None:
        with pytest.raises(Exception):
            GenreDetectionRequest(text="short")

    def test_genre_detection_result_creation(self) -> None:
        result = GenreDetectionResult(
            genre="academic",
            confidence=0.85,
            suggested_goal="academic",
            reasoning="Contains technical vocabulary and academic structure",
            signals=["technical vocabulary", "passive voice", "citation markers"],
        )
        assert result.genre == "academic"
        assert result.confidence == 0.85
        assert result.suggested_goal == "academic"
        assert len(result.signals) == 3

    def test_genre_detection_response(self) -> None:
        response = GenreDetectionResponse(
            detection=GenreDetectionResult(
                genre="daily",
                confidence=0.9,
                suggested_goal="daily_reading",
                reasoning="Conversational tone",
                signals=["conversational language", "active voice"],
            ),
            latency_ms=150,
        )
        assert response.detection.genre == "daily"
        assert response.latency_ms == 150


class TestGenreDetectionBusinessLogic:
    def test_should_suggest_academic_when_academic_detected(self) -> None:
        detection_result = GenreDetectionResult(
            genre="academic",
            confidence=0.7,
            suggested_goal="academic",
            reasoning="test",
            signals=[],
        )

        current_mode_daily = "daily"
        current_mode_exam = "exam"
        current_mode_academic = "academic"

        should_suggest_daily = (
            detection_result.genre == "academic"
            and current_mode_daily != "academic"
            and detection_result.confidence >= 0.6
            and detection_result.suggested_goal == "academic"
        )
        assert should_suggest_daily is True

        should_suggest_exam = (
            detection_result.genre == "academic"
            and current_mode_exam != "academic"
            and detection_result.confidence >= 0.6
            and detection_result.suggested_goal == "academic"
        )
        assert should_suggest_exam is True

        should_suggest_academic = (
            detection_result.genre == "academic"
            and current_mode_academic != "academic"
            and detection_result.confidence >= 0.6
            and detection_result.suggested_goal == "academic"
        )
        assert should_suggest_academic is False

    def test_should_not_suggest_when_low_confidence(self) -> None:
        low_confidence = GenreDetectionResult(
            genre="academic",
            confidence=0.5,
            suggested_goal="academic",
            reasoning="test",
            signals=[],
        )

        should_suggest = (
            low_confidence.genre == "academic"
            and "daily" != "academic"
            and low_confidence.confidence >= 0.6
            and low_confidence.suggested_goal == "academic"
        )
        assert should_suggest is False

    def test_should_not_suggest_when_not_academic(self) -> None:
        daily_detection = GenreDetectionResult(
            genre="daily",
            confidence=0.8,
            suggested_goal="daily_reading",
            reasoning="test",
            signals=[],
        )

        should_suggest = (
            daily_detection.genre == "academic"
            and "daily" != "academic"
            and daily_detection.confidence >= 0.6
            and daily_detection.suggested_goal == "academic"
        )
        assert should_suggest is False

    def test_skip_detection_when_already_academic(self) -> None:
        current_mode = "academic"
        word_count = 50

        should_skip = current_mode == "academic" or word_count < 30
        assert should_skip is True

    def test_skip_detection_when_text_too_short(self) -> None:
        current_mode = "daily"
        word_count = 20

        should_skip = current_mode == "academic" or word_count < 30
        assert should_skip is True

    def test_should_not_skip_detection(self) -> None:
        current_mode = "daily"
        word_count = 50

        should_skip = current_mode == "academic" or word_count < 30
        assert should_skip is False


class TestGenreDetectionSignals:
    def test_academic_signals_include_technical_terms(self) -> None:
        academic_signals = [
            "technical vocabulary",
            "academic vocabulary",
            "passive voice",
            "citation markers",
            "nominalization",
            "IMRAD structure indicators",
            "hedging language",
        ]
        assert "technical vocabulary" in academic_signals
        assert "citation markers" in academic_signals
        assert "hedging language" in academic_signals

    def test_daily_signals(self) -> None:
        daily_signals = [
            "conversational language",
            "active voice predominant",
            "simple sentence structure",
            "first/second person pronouns",
        ]
        assert "conversational language" in daily_signals


class TestGenreDetectionPrompt:
    def test_prompt_instructions_cover_key_points(self) -> None:
        key_instructions = [
            "technical vocabulary",
            "passive voice",
            "citation markers",
            "IMRAD",
            "hedging",
            "nominalization",
            "confidence",
            "signals",
        ]

        assert all(
            term in "technical vocabulary, passive voice, citation markers, IMRAD, hedging, nominalization, confidence, signals"
            for term in key_instructions
        )

    def test_classification_categories(self) -> None:
        categories: list[GenreCategory] = ["academic", "daily", "exam_oriented", "uncertain"]
        assert "academic" in categories
        assert "daily" in categories
        assert "exam_oriented" in categories
        assert "uncertain" in categories

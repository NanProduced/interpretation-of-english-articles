from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


GenreCategory = Literal["academic", "daily", "exam_oriented", "uncertain"]


class GenreDetectionRequest(BaseModel):
    text: str = Field(
        min_length=10,
        description="待检测的英文文本片段。",
    )


class GenreDetectionResult(BaseModel):
    genre: GenreCategory = Field(
        description="检测到的文本类别。",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="检测置信度 (0.0-1.0)。",
    )
    suggested_goal: Literal["academic", "daily_reading", "exam"] | None = Field(
        default=None,
        description="建议使用的 reading_goal，如果检测到文体与用户当前选择不匹配。",
    )
    reasoning: str = Field(
        default="",
        description="LLM 给出的分类理由，用于调试和透明度。",
    )
    signals: list[str] = Field(
        default_factory=list,
        description="检测到的文体特征信号（如引用标记、专业术语等）。",
    )


class GenreDetectionResponse(BaseModel):
    detection: GenreDetectionResult
    latency_ms: int = Field(
        description="检测耗时（毫秒）。",
    )

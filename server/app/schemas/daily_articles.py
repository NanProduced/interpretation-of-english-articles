"""
Daily Articles API Schemas.

Defines request/response Pydantic models for daily articles endpoints.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


SourceProvider = Literal["spaceflight_news", "newsapi", "wikipedia", "other", "combined"]
ArticleStatus = Literal["active", "archived", "hidden"]
FetchStatus = Literal["success", "partial", "failed"]


class DailyArticle(BaseModel):
    """Daily article model."""

    id: UUID
    source_provider: SourceProvider
    source_id: str
    title: str
    content: str
    content_word_count: int = Field(ge=0)
    source_url: str
    image_url: str | None = None
    publish_date: date | None = None
    fetch_date: date
    language: str = Field(default="en")
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    status: ArticleStatus = Field(default="active")
    created_at: datetime
    updated_at: datetime


class DailyArticleSummary(BaseModel):
    """Daily article summary model (without full content for list views)."""

    id: UUID
    source_provider: SourceProvider
    title: str
    content_word_count: int = Field(ge=0)
    source_url: str
    image_url: str | None = None
    publish_date: date | None = None
    fetch_date: date
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class DailyArticleFetchLog(BaseModel):
    """Fetch log model."""

    id: UUID
    fetch_date: date
    source_provider: SourceProvider
    status: FetchStatus
    articles_fetched: int
    articles_valid: int
    articles_saved: int
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: datetime


class GetTodayArticlesResponse(BaseModel):
    """Response for GET /daily-articles/today."""

    date: date
    articles: list[DailyArticleSummary]
    total_count: int


class GetArticleResponse(BaseModel):
    """Response for GET /daily-articles/{id}."""

    article: DailyArticle


class ManualFetchTriggerResponse(BaseModel):
    """Response for POST /daily-articles/fetch."""

    success: bool
    message: str
    fetch_log: DailyArticleFetchLog | None = None


class FetchStatistics(BaseModel):
    """Fetch statistics for a specific date."""

    date: date
    total_articles: int
    total_fetches: int
    last_fetch_status: FetchStatus | None = None
    last_fetch_at: datetime | None = None


class GetFetchStatsResponse(BaseModel):
    """Response for GET /daily-articles/stats."""

    stats: FetchStatistics
